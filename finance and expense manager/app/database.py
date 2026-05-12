import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

from .config import BASE_DIR, get_settings
from .security import hash_password


def db_path() -> Path:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise RuntimeError("This starter is configured for SQLite. Set sqlite:///path in DATABASE_URL.")
    return Path(url.replace("sqlite:///", "", 1))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    schema = (BASE_DIR / "app" / "schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.executescript(schema)
        count = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if count == 0:
            seed_demo(conn)


def seed_demo(conn: sqlite3.Connection) -> None:
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role,currency,created_at) VALUES(?,?,?,?,?,?)",
        ("Ava Sterling", "demo@finance.ai", hash_password("Demo@12345"), "admin", "USD", now),
    )
    user_id = conn.execute("SELECT id FROM users WHERE email=?", ("demo@finance.ai",)).fetchone()["id"]
    categories = [
        ("Housing", 1900), ("Food", 760), ("Transport", 420), ("Utilities", 360),
        ("Shopping", 520), ("Health", 280), ("Travel", 600), ("Entertainment", 300),
        ("Education", 240), ("Investments", 1400),
    ]
    for cat, limit_amount in categories:
        conn.execute(
            "INSERT INTO budgets(user_id,category,limit_amount,period,created_at) VALUES(?,?,?,?,?)",
            (user_id, cat, limit_amount, "monthly", now),
        )

    merchants = [
        ("CloudRent", "Housing", 1850, "expense"),
        ("Green Basket", "Food", 92, "expense"),
        ("Metro Card", "Transport", 48, "expense"),
        ("Nebula Power", "Utilities", 136, "expense"),
        ("Aurora Salary", "Salary", 7200, "income"),
        ("Market Fund", "Investments", 750, "expense"),
        ("StreamHub", "Subscriptions", 19, "expense"),
        ("Pulse Pharmacy", "Health", 65, "expense"),
        ("Orbit Cafe", "Food", 34, "expense"),
        ("Luxe Mall", "Shopping", 180, "expense"),
    ]
    start = date.today().replace(day=1) - timedelta(days=210)
    for i in range(170):
        merchant, category, amount, kind = merchants[i % len(merchants)]
        tx_date = start + timedelta(days=i * 2)
        drift = 1 + ((i % 13) - 6) / 100
        final_amount = round(amount * drift + (i % 7) * 2.4, 2)
        if i in (63, 128):
            merchant, category, final_amount, kind = ("Unknown Crypto Gateway", "Suspicious", 1850 + i * 6, "expense")
        conn.execute(
            """
            INSERT INTO transactions(user_id,kind,amount,currency,category,merchant,description,occurred_on,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (user_id, kind, final_amount, "USD", category, merchant, f"{merchant} {category}", tx_date.isoformat(), now),
        )

    for name, target, saved, deadline in [
        ("Emergency Reserve", 15000, 8250, "2026-12-31"),
        ("Japan Design Trip", 6500, 2480, "2026-10-15"),
        ("Home Studio", 3200, 1180, "2026-08-01"),
    ]:
        conn.execute(
            "INSERT INTO goals(user_id,name,target_amount,saved_amount,deadline,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, name, target, saved, deadline, now),
        )

    for name, amount, due, category in [
        ("StreamHub Pro", 19, 5, "Subscriptions"),
        ("Cloud Storage", 12, 12, "Subscriptions"),
        ("Insurance Premium", 140, 20, "Health"),
    ]:
        conn.execute(
            "INSERT INTO reminders(user_id,name,amount,currency,due_day,category,active,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (user_id, name, amount, "USD", due, category, 1, now),
        )
