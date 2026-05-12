import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, pstdev


CATEGORY_KEYWORDS = {
    "Food": ["restaurant", "cafe", "coffee", "grocery", "market", "basket", "pizza", "food", "dining"],
    "Transport": ["uber", "taxi", "metro", "fuel", "gas", "parking", "train", "bus", "flight"],
    "Housing": ["rent", "mortgage", "lease", "apartment"],
    "Utilities": ["power", "electric", "water", "internet", "mobile", "utility", "broadband"],
    "Shopping": ["mall", "amazon", "store", "shop", "luxe", "fashion"],
    "Health": ["pharmacy", "doctor", "clinic", "insurance", "health", "pulse"],
    "Travel": ["hotel", "airline", "booking", "trip", "travel"],
    "Entertainment": ["movie", "stream", "game", "music", "theater"],
    "Education": ["course", "book", "school", "tuition", "academy"],
    "Investments": ["fund", "stock", "broker", "investment", "sip"],
    "Salary": ["salary", "payroll", "income", "bonus"],
    "Subscriptions": ["subscription", "streamhub", "storage", "netflix", "spotify"],
}


def classify_expense(text: str, amount: float = 0) -> tuple[str, float]:
    corpus = text.lower()
    scores: dict[str, int] = {}
    for category, words in CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for word in words if word in corpus)
    best, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        if amount > 1200:
            return "Housing", 0.46
        if amount > 600:
            return "Travel", 0.42
        return "General", 0.35
    return best, min(0.98, 0.58 + score * 0.14)


def parse_voice_expense(transcript: str) -> dict:
    text = transcript.lower()
    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    amount = float(amount_match.group(1)) if amount_match else 0.0
    merchant = re.sub(r"\b(add|spent|paid|expense|income|earned|for|on|rs|usd|dollars|rupees)\b", "", text)
    merchant = re.sub(r"\d+(?:\.\d+)?", "", merchant).strip().title() or "Voice Entry"
    kind = "income" if any(w in text for w in ["earned", "salary", "received", "income"]) else "expense"
    category, confidence = classify_expense(text, amount)
    return {"kind": kind, "amount": amount, "merchant": merchant, "description": transcript, "category": category, "confidence": confidence}


def extract_receipt_text(payload: bytes, filename: str) -> dict:
    try:
        text = payload.decode("utf-8", errors="ignore")
    except Exception:
        text = filename
    amount_candidates = [float(x) for x in re.findall(r"(?<!\d)(\d{1,6}(?:\.\d{1,2})?)(?!\d)", text)]
    amount = max(amount_candidates) if amount_candidates else 0.0
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    merchant = lines[0][:80] if lines else filename.rsplit(".", 1)[0].replace("_", " ").title()
    category, confidence = classify_expense(f"{merchant} {text}", amount)
    return {"merchant": merchant, "amount": amount, "category": category, "confidence": confidence, "raw_text": text[:2000]}


def monthly_totals(transactions: list[dict]) -> list[dict]:
    buckets = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for tx in transactions:
        month = tx["occurred_on"][:7]
        buckets[month][tx["kind"]] += float(tx["amount"])
    return [{"month": k, "income": round(v["income"], 2), "expense": round(v["expense"], 2)} for k, v in sorted(buckets.items())]


def forecast_expenses(transactions: list[dict], months: int = 6) -> list[dict]:
    series = monthly_totals(transactions)
    expense_points = [(i + 1, row["expense"]) for i, row in enumerate(series) if row["expense"] > 0]
    if not expense_points:
        return []
    xs = [p[0] for p in expense_points]
    ys = [p[1] for p in expense_points]
    xbar, ybar = mean(xs), mean(ys)
    denom = sum((x - xbar) ** 2 for x in xs) or 1
    slope = sum((x - xbar) * (y - ybar) for x, y in expense_points) / denom
    intercept = ybar - slope * xbar
    last_month = datetime.strptime(series[-1]["month"] + "-01", "%Y-%m-%d").date() if series else date.today().replace(day=1)
    forecast = []
    for step in range(1, months + 1):
        month_date = (last_month + timedelta(days=32 * step)).replace(day=1)
        predicted = max(0, intercept + slope * (len(series) + step))
        forecast.append({"month": month_date.strftime("%Y-%m"), "predicted_expense": round(predicted, 2)})
    return forecast


def detect_anomalies(transactions: list[dict]) -> list[dict]:
    expenses = [float(tx["amount"]) for tx in transactions if tx["kind"] == "expense"]
    if len(expenses) < 5:
        return []
    avg = mean(expenses)
    sigma = pstdev(expenses) or 1
    anomalies = []
    for tx in transactions:
        if tx["kind"] != "expense":
            continue
        amount = float(tx["amount"])
        z = (amount - avg) / sigma
        risky_merchant = any(word in tx["merchant"].lower() for word in ["unknown", "crypto", "wire", "gateway"])
        if z > 2.0 or risky_merchant:
            item = dict(tx)
            item["risk_score"] = min(99, round(55 + max(z, 0) * 15 + (20 if risky_merchant else 0)))
            item["reason"] = "Unusual merchant and/or amount outside normal spending range"
            anomalies.append(item)
    return sorted(anomalies, key=lambda x: x["risk_score"], reverse=True)[:8]


def behavior_insights(transactions: list[dict], budgets: list[dict]) -> dict:
    expenses = [tx for tx in transactions if tx["kind"] == "expense"]
    income = sum(float(tx["amount"]) for tx in transactions if tx["kind"] == "income")
    spent = sum(float(tx["amount"]) for tx in expenses)
    by_cat = Counter()
    for tx in expenses:
        by_cat[tx["category"]] += float(tx["amount"])
    top = by_cat.most_common(5)
    savings_rate = 0 if income <= 0 else max(0, (income - spent) / income)
    budget_map = {b["category"]: float(b["limit_amount"]) for b in budgets}
    alerts = []
    for category, amount in by_cat.items():
        limit = budget_map.get(category)
        if limit and amount > limit:
            alerts.append({"category": category, "message": f"{category} is {round((amount / limit - 1) * 100)}% over budget", "level": "danger"})
        elif limit and amount > limit * 0.85:
            alerts.append({"category": category, "message": f"{category} is nearing its budget", "level": "warning"})
    health = 100
    health -= min(35, round((spent / max(income, 1)) * 30))
    health += min(20, round(savings_rate * 35))
    health -= min(20, len(alerts) * 4)
    health = max(20, min(98, health))
    recommendations = []
    if top:
        recommendations.append(f"Your largest spending area is {top[0][0]}. Set a weekly cap to reduce variance.")
    if savings_rate < 0.2:
        recommendations.append("Automate a savings transfer on income days to lift your savings rate above 20%.")
    if alerts:
        recommendations.append("Pause non-essential purchases in categories with active budget alerts.")
    recommendations.append("Review recurring payments weekly and cancel unused subscriptions.")
    return {
        "top_categories": [{"category": cat, "amount": round(amount, 2)} for cat, amount in top],
        "savings_rate": round(savings_rate * 100, 1),
        "health_score": health,
        "alerts": alerts[:10],
        "recommendations": recommendations,
    }


def assistant_reply(message: str, dashboard: dict) -> str:
    text = message.lower()
    score = dashboard.get("health_score", 0)
    if "save" in text or "saving" in text:
        return f"Your health score is {score}. Start with the top category, then schedule an automatic transfer equal to 10% of monthly income."
    if "budget" in text:
        alerts = dashboard.get("alerts", [])
        if alerts:
            return f"Budget pressure detected: {alerts[0]['message']}. I recommend a 7-day freeze on discretionary spend in that category."
        return "Budgets are under control. Increase savings goals or lower one category limit by 5% to improve discipline."
    if "fraud" in text or "anomaly" in text:
        anomalies = dashboard.get("anomalies", [])
        return f"I found {len(anomalies)} suspicious transactions. Review the highest risk merchant first." if anomalies else "No high-risk transaction pattern is currently visible."
    return f"You have a financial health score of {score}. Focus on budget alerts, recurring payments, and your highest-spend category for the fastest improvement."
