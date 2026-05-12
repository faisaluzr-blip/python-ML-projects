import asyncio
import csv
import io
from datetime import date, datetime
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, CURRENCIES
from .database import connect, init_db
from .ml_engine import (
    assistant_reply,
    behavior_insights,
    classify_expense,
    detect_anomalies,
    extract_receipt_text,
    forecast_expenses,
    monthly_totals,
    parse_voice_expense,
)
from .schemas import AssistantIn, BudgetIn, GoalIn, LoginIn, ReminderIn, SignupIn, TransactionIn, VoiceIn
from .security import bearer_token, create_token, decode_token, hash_password, verify_password


app = FastAPI(title="AI Finance Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


def row_to_dict(row: Any) -> dict:
    return dict(row) if row is not None else {}


def current_user(request: Request) -> dict:
    payload = decode_token(bearer_token(request))
    with connect() as conn:
        user = conn.execute("SELECT id,name,email,role,currency,created_at FROM users WHERE id=?", (payload["sub"],)).fetchone()
        if not user:
            raise HTTPException(401, "User not found")
        return row_to_dict(user)


def user_transactions(user_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY occurred_on DESC, id DESC",
            (user_id,),
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def user_budgets(user_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM budgets WHERE user_id=? ORDER BY category", (user_id,)).fetchall()
        return [row_to_dict(r) for r in rows]


def build_dashboard(user_id: int) -> dict:
    transactions = user_transactions(user_id)
    budgets = user_budgets(user_id)
    insights = behavior_insights(transactions, budgets)
    anomalies = detect_anomalies(transactions)
    totals = {
        "income": round(sum(float(tx["amount"]) for tx in transactions if tx["kind"] == "income"), 2),
        "expense": round(sum(float(tx["amount"]) for tx in transactions if tx["kind"] == "expense"), 2),
    }
    totals["net"] = round(totals["income"] - totals["expense"], 2)
    return {
        **totals,
        **insights,
        "monthly": monthly_totals(transactions),
        "forecast": forecast_expenses(transactions),
        "anomalies": anomalies,
        "recent_transactions": transactions[:12],
        "budgets": budgets,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "frontend" / "index.html").read_text(encoding="utf-8"))


@app.post("/api/auth/signup")
def signup(payload: SignupIn) -> dict:
    now = datetime.utcnow().isoformat()
    with connect() as conn:
        exists = conn.execute("SELECT id FROM users WHERE email=?", (payload.email.lower(),)).fetchone()
        if exists:
            raise HTTPException(409, "Email is already registered")
        conn.execute(
            "INSERT INTO users(name,email,password_hash,role,currency,created_at) VALUES(?,?,?,?,?,?)",
            (payload.name, payload.email.lower(), hash_password(payload.password), "user", payload.currency.upper(), now),
        )
        user = conn.execute("SELECT id,name,email,role,currency,created_at FROM users WHERE email=?", (payload.email.lower(),)).fetchone()
    user_dict = row_to_dict(user)
    return {"access_token": create_token(str(user_dict["id"]), user_dict["role"]), "token_type": "bearer", "user": user_dict}


@app.post("/api/auth/login")
def login(payload: LoginIn) -> dict:
    with connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (payload.email.lower(),)).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    safe_user = {k: user[k] for k in ("id", "name", "email", "role", "currency", "created_at")}
    return {"access_token": create_token(str(user["id"]), user["role"]), "token_type": "bearer", "user": safe_user}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


@app.get("/api/currencies")
def currencies() -> dict:
    return {"currencies": [c.model_dump() for c in CURRENCIES.values()]}


@app.get("/api/dashboard")
def dashboard(user: dict = Depends(current_user)) -> dict:
    return build_dashboard(user["id"])


@app.get("/api/transactions")
def list_transactions(user: dict = Depends(current_user)) -> dict:
    return {"transactions": user_transactions(user["id"])}


@app.post("/api/transactions")
def create_transaction(payload: TransactionIn, user: dict = Depends(current_user)) -> dict:
    category = payload.category
    confidence = 1.0
    if not category:
        category, confidence = classify_expense(f"{payload.merchant} {payload.description}", payload.amount)
    now = datetime.utcnow().isoformat()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO transactions(user_id,kind,amount,currency,category,merchant,description,occurred_on,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (user["id"], payload.kind, payload.amount, payload.currency.upper(), category, payload.merchant, payload.description, payload.occurred_on, now),
        )
        tx = conn.execute("SELECT * FROM transactions WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"transaction": row_to_dict(tx), "ai": {"category": category, "confidence": confidence}}


@app.delete("/api/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, user: dict = Depends(current_user)) -> dict:
    with connect() as conn:
        conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (transaction_id, user["id"]))
    return {"ok": True}


@app.post("/api/transactions/voice")
def create_voice_transaction(payload: VoiceIn, user: dict = Depends(current_user)) -> dict:
    parsed = parse_voice_expense(payload.transcript)
    if parsed["amount"] <= 0:
        raise HTTPException(422, "Could not detect an amount from the transcript")
    tx = TransactionIn(
        kind=parsed["kind"],
        amount=parsed["amount"],
        currency=user["currency"],
        category=parsed["category"],
        merchant=parsed["merchant"],
        description=payload.transcript,
        occurred_on=payload.occurred_on or date.today().isoformat(),
    )
    result = create_transaction(tx, user)
    result["voice"] = parsed
    return result


@app.post("/api/ocr/receipt")
async def receipt_scan(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    payload = await file.read()
    scan = extract_receipt_text(payload, file.filename or "receipt")
    return {"scan": scan, "ready_transaction": {"kind": "expense", "currency": user["currency"], "occurred_on": date.today().isoformat(), **scan}}


@app.get("/api/budgets")
def budgets(user: dict = Depends(current_user)) -> dict:
    return {"budgets": user_budgets(user["id"])}


@app.post("/api/budgets")
def upsert_budget(payload: BudgetIn, user: dict = Depends(current_user)) -> dict:
    now = datetime.utcnow().isoformat()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO budgets(user_id,category,limit_amount,period,created_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id,category,period) DO UPDATE SET limit_amount=excluded.limit_amount
            """,
            (user["id"], payload.category, payload.limit_amount, payload.period, now),
        )
    return {"ok": True, "budget": payload.model_dump()}


@app.get("/api/goals")
def goals(user: dict = Depends(current_user)) -> dict:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM goals WHERE user_id=? ORDER BY deadline", (user["id"],)).fetchall()
    return {"goals": [row_to_dict(r) for r in rows]}


@app.post("/api/goals")
def create_goal(payload: GoalIn, user: dict = Depends(current_user)) -> dict:
    now = datetime.utcnow().isoformat()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO goals(user_id,name,target_amount,saved_amount,deadline,created_at) VALUES(?,?,?,?,?,?)",
            (user["id"], payload.name, payload.target_amount, payload.saved_amount, payload.deadline, now),
        )
        row = conn.execute("SELECT * FROM goals WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"goal": row_to_dict(row)}


@app.get("/api/reminders")
def reminders(user: dict = Depends(current_user)) -> dict:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM reminders WHERE user_id=? ORDER BY due_day", (user["id"],)).fetchall()
    return {"reminders": [row_to_dict(r) for r in rows]}


@app.post("/api/reminders")
def create_reminder(payload: ReminderIn, user: dict = Depends(current_user)) -> dict:
    now = datetime.utcnow().isoformat()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO reminders(user_id,name,amount,currency,due_day,category,active,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (user["id"], payload.name, payload.amount, payload.currency, payload.due_day, payload.category, int(payload.active), now),
        )
        row = conn.execute("SELECT * FROM reminders WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"reminder": row_to_dict(row)}


@app.post("/api/assistant")
def assistant(payload: AssistantIn, user: dict = Depends(current_user)) -> dict:
    data = build_dashboard(user["id"])
    return {"reply": assistant_reply(payload.message, data), "context": {"health_score": data["health_score"], "alerts": data["alerts"][:3]}}


@app.get("/api/export/{kind}")
def export_report(kind: str, user: dict = Depends(current_user)) -> StreamingResponse:
    transactions = user_transactions(user["id"])
    if kind not in {"csv", "excel", "pdf"}:
        raise HTTPException(404, "Supported exports: csv, excel, pdf")
    if kind == "pdf":
        text = io.StringIO()
        text.write("Finance Intelligence Report\n\n")
        dash = build_dashboard(user["id"])
        text.write(f"Income: {dash['income']}  Expense: {dash['expense']}  Net: {dash['net']}  Health: {dash['health_score']}\n\n")
        for tx in transactions[:80]:
            text.write(f"{tx['occurred_on']} | {tx['kind']} | {tx['category']} | {tx['merchant']} | {tx['amount']} {tx['currency']}\n")
        return StreamingResponse(iter([text.getvalue().encode()]), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=finance-report.pdf"})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "occurred_on", "kind", "amount", "currency", "category", "merchant", "description"])
    writer.writeheader()
    for tx in transactions:
        writer.writerow({field: tx[field] for field in writer.fieldnames})
    filename = "transactions.xlsx" if kind == "excel" else "transactions.csv"
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if kind == "excel" else "text/csv"
    return StreamingResponse(iter([output.getvalue().encode()]), media_type=media, headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/api/admin/overview")
def admin_overview(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    with connect() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        txs = conn.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()["c"]
        volume = conn.execute("SELECT COALESCE(SUM(amount),0) AS s FROM transactions").fetchone()["s"]
    return {"users": users, "transactions": txs, "managed_volume": round(volume, 2), "system_status": "operational"}


@app.get("/api/stream")
async def stream(user: dict = Depends(current_user)) -> StreamingResponse:
    async def events():
        for _ in range(120):
            data = build_dashboard(user["id"])
            yield f"data: {JSONResponse(content={'net': data['net'], 'expense': data['expense'], 'health_score': data['health_score'], 'alerts': len(data['alerts'])}).body.decode()}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(events(), media_type="text/event-stream")
