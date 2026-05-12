import sqlite3
from dataclasses import dataclass
from pathlib import Path

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "app.db"


def get_connection():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class User(UserMixin):
    id: int
    name: str
    email: str
    role: str
    farm_name: str

    @staticmethod
    def get(user_id):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User(row["id"], row["name"], row["email"], row["role"], row["farm_name"]) if row else None

    @staticmethod
    def authenticate(email, password):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return User(row["id"], row["name"], row["email"], row["role"], row["farm_name"])
        return None


def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                farm_name TEXT NOT NULL DEFAULT 'Green Valley Farm'
            );
            CREATE TABLE IF NOT EXISTS farmers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                crop TEXT NOT NULL,
                acreage REAL NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS crop_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop TEXT NOT NULL,
                soil_type TEXT NOT NULL,
                health_score INTEGER NOT NULL,
                yield_estimate REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                soil_moisture REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                ph REAL NOT NULL,
                nitrogen REAL NOT NULL,
                phosphorus REAL NOT NULL,
                potassium REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        if not conn.execute("SELECT 1 FROM users WHERE email = ?", ("admin@agri.ai",)).fetchone():
            conn.execute(
                "INSERT INTO users(name,email,password_hash,role,farm_name) VALUES(?,?,?,?,?)",
                (
                    "Agri Admin",
                    "admin@agri.ai",
                    generate_password_hash("admin123"),
                    "admin",
                    "Green Valley Farm",
                ),
            )

        if not conn.execute("SELECT 1 FROM farmers").fetchone():
            conn.executemany(
                "INSERT INTO farmers(name,location,crop,acreage,status) VALUES(?,?,?,?,?)",
                [
                    ("Aisha Khan", "Punjab", "Wheat", 14.5, "Active"),
                    ("Ravi Kumar", "Maharashtra", "Cotton", 9.2, "Monitoring"),
                    ("Meera Das", "West Bengal", "Rice", 18.0, "Active"),
                    ("Kabir Singh", "Karnataka", "Tomato", 5.6, "Alert"),
                ],
            )
        conn.commit()
