from __future__ import annotations

"""
IRIS Core -- SQLite database operations.
Handles user registration, commitment tracking, and rate limiting.
"""

import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from config import DB_PATH


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_count_today INTEGER DEFAULT 0,
            last_message_date DATE,
            timezone TEXT DEFAULT 'America/Phoenix'
        );

        CREATE TABLE IF NOT EXISTS commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            check_in_time TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checked_in_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            exchange_count INTEGER DEFAULT 0,
            session_type TEXT DEFAULT 'accountability',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE INDEX IF NOT EXISTS idx_commitments_status
            ON commitments(status, check_in_time);
        CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON sessions(telegram_id, closed_at);
    """)
    conn.commit()
    conn.close()


# ---- User operations ----

def add_user(telegram_id: int, email: str) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, email) VALUES (?, ?)",
            (telegram_id, email)
        )
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def is_whitelisted(telegram_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return row is not None


def get_user(telegram_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- Rate limiting ----

def check_rate_limit(telegram_id: int, daily_limit: int) -> bool:
    """Returns True if user is within their daily limit."""
    conn = get_connection()
    row = conn.execute(
        "SELECT message_count_today, last_message_date FROM users WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()

    if not row:
        return False

    today = date.today().isoformat()
    if row["last_message_date"] != today:
        return True  # New day, counter resets

    return row["message_count_today"] < daily_limit


def increment_message_count(telegram_id: int):
    conn = get_connection()
    today = date.today().isoformat()
    conn.execute("""
        UPDATE users
        SET message_count_today = CASE
            WHEN last_message_date = ? THEN message_count_today + 1
            ELSE 1
        END,
        last_message_date = ?
        WHERE telegram_id = ?
    """, (today, today, telegram_id))
    conn.commit()
    conn.close()


# ---- Commitment operations ----

def add_commitment(telegram_id: int, task: str, check_in_time: datetime) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO commitments (telegram_id, task, check_in_time) VALUES (?, ?, ?)",
        (telegram_id, task, check_in_time.isoformat())
    )
    conn.commit()
    commit_id = cursor.lastrowid
    conn.close()
    return commit_id


def get_due_checkins() -> list[dict]:
    """Get all pending commitments where check_in_time has passed."""
    conn = get_connection()
    now = datetime.now().isoformat()
    rows = conn.execute("""
        SELECT c.*, u.telegram_id
        FROM commitments c
        JOIN users u ON c.telegram_id = u.telegram_id
        WHERE c.status = 'pending' AND c.check_in_time <= ?
    """, (now,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_commitment_status(commit_id: int, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE commitments SET status = ?, checked_in_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), commit_id)
    )
    conn.commit()
    conn.close()


def get_active_commitments(telegram_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM commitments
        WHERE telegram_id = ? AND status = 'pending'
        ORDER BY check_in_time ASC
    """, (telegram_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_stale_commitments(hours: int = 24):
    """Mark commitments as missed if check_in_time was more than `hours` ago."""
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    conn.execute("""
        UPDATE commitments
        SET status = 'missed'
        WHERE status = 'pending' AND check_in_time <= ?
    """, (cutoff,))
    conn.commit()
    conn.close()


# ---- Session tracking ----

def get_active_session(telegram_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM sessions
        WHERE telegram_id = ? AND closed_at IS NULL
        ORDER BY started_at DESC LIMIT 1
    """, (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(telegram_id: int, session_type: str = "accountability") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO sessions (telegram_id, session_type) VALUES (?, ?)",
        (telegram_id, session_type)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def increment_exchange(session_id: int) -> int:
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET exchange_count = exchange_count + 1 WHERE id = ?",
        (session_id,)
    )
    conn.commit()
    row = conn.execute(
        "SELECT exchange_count FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row["exchange_count"] if row else 0


def close_session(session_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET closed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), session_id)
    )
    conn.commit()
    conn.close()


# ---- Email signup (pending registrations) ----

def add_pending_signup(email: str, signup_token: str):
    """Store a pending signup before the user messages the bot."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_signups (
            email TEXT PRIMARY KEY,
            signup_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            claimed INTEGER DEFAULT 0
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO pending_signups (email, signup_token) VALUES (?, ?)",
        (email, signup_token)
    )
    conn.commit()
    conn.close()


def claim_signup(signup_token: str, telegram_id: int) -> str | None:
    """Link a Telegram user to their email signup. Returns email or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT email FROM pending_signups WHERE signup_token = ? AND claimed = 0",
        (signup_token,)
    ).fetchone()
    if row:
        email = row["email"]
        conn.execute(
            "UPDATE pending_signups SET claimed = 1 WHERE signup_token = ?",
            (signup_token,)
        )
        conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, email) VALUES (?, ?)",
            (telegram_id, email)
        )
        conn.commit()
        conn.close()
        return email
    conn.close()
    return None
