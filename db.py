import sqlite3
import secrets
from datetime import datetime

DB_PATH = "stage317.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        plan TEXT NOT NULL DEFAULT 'free',
        stripe_customer_id TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        plan TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stripe_session_id TEXT UNIQUE,
        email TEXT NOT NULL,
        plan TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def create_or_update_user(email, plan="free", stripe_customer_id=None):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("""
    INSERT INTO users (email, plan, stripe_customer_id, created_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET
        plan=excluded.plan,
        stripe_customer_id=COALESCE(excluded.stripe_customer_id, users.stripe_customer_id)
    """, (email, plan, stripe_customer_id, now))

    conn.commit()
    conn.close()


def generate_api_key(email, plan):
    key = "remeda_" + secrets.token_urlsafe(32)
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("""
    INSERT INTO api_keys (api_key, email, plan, active, created_at)
    VALUES (?, ?, ?, 1, ?)
    """, (key, email, plan, now))

    conn.commit()
    conn.close()
    return key


def get_plan_by_api_key(api_key):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT plan FROM api_keys
    WHERE api_key=? AND active=1
    """, (api_key,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return row[0]


def save_payment(session_id, email, plan, status):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("""
    INSERT OR IGNORE INTO payments (stripe_session_id, email, plan, status, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (session_id, email, plan, status, now))

    conn.commit()
    conn.close()


def list_keys_for_email(email):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT api_key, plan, active, created_at
    FROM api_keys
    WHERE email=?
    ORDER BY id DESC
    """, (email,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "api_key": r[0],
            "plan": r[1],
            "active": bool(r[2]),
            "created_at": r[3]
        }
        for r in rows
    ]


def seed_demo_keys():
    create_or_update_user("demo-free@example.com", "free")
    create_or_update_user("demo-pro@example.com", "pro")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM api_keys WHERE api_key='test-key-123'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO api_keys (api_key, email, plan, active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """, ("test-key-123", "demo-free@example.com", "free", datetime.utcnow().isoformat()))

    cur.execute("SELECT COUNT(*) FROM api_keys WHERE api_key='pro-key-456'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO api_keys (api_key, email, plan, active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """, ("pro-key-456", "demo-pro@example.com", "pro", datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()
