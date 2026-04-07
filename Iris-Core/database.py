from __future__ import annotations

"""
IRIS Core -- SQLite database operations.
Handles user registration, Mt. Everest session tracking, and rate limiting.
"""

import sqlite3
from datetime import date
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

        CREATE TABLE IF NOT EXISTS mt_everest_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            status TEXT DEFAULT 'excavating',
            summary TEXT,
            email_sent INTEGER DEFAULT 0,
            exchange_count INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            followup_1d_sent INTEGER DEFAULT 0,
            followup_3d_sent INTEGER DEFAULT 0,
            followup_5d_sent INTEGER DEFAULT 0,
            followup_7d_email_sent INTEGER DEFAULT 0,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );
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


def get_user_email(telegram_id: int) -> str | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT email FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return row["email"] if row else None


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


# ---- Mt. Everest session operations ----

def get_session(telegram_id: int) -> dict | None:
    """Get the user's Mt. Everest session."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM mt_everest_sessions WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(telegram_id: int) -> int:
    """Create a new Mt. Everest session. Returns session ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO mt_everest_sessions (telegram_id) VALUES (?)",
        (telegram_id,)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def increment_exchange(telegram_id: int) -> int:
    """Increment exchange count and return new count."""
    conn = get_connection()
    conn.execute(
        "UPDATE mt_everest_sessions SET exchange_count = exchange_count + 1 WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    row = conn.execute(
        "SELECT exchange_count FROM mt_everest_sessions WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return row["exchange_count"] if row else 0


def get_session_status(telegram_id: int) -> str | None:
    """Get the current session status: excavating, completed, upgrade_only."""
    session = get_session(telegram_id)
    return session["status"] if session else None


def save_summary(telegram_id: int, summary_text: str):
    """Save the Mt. Everest summary and mark session as completed."""
    from datetime import datetime
    conn = get_connection()
    conn.execute("""
        UPDATE mt_everest_sessions
        SET summary = ?, status = 'completed', completed_at = ?
        WHERE telegram_id = ?
    """, (summary_text, datetime.now().isoformat(), telegram_id))
    conn.commit()
    conn.close()


def mark_upgrade_only(telegram_id: int):
    """Transition session to upgrade_only state."""
    conn = get_connection()
    conn.execute(
        "UPDATE mt_everest_sessions SET status = 'upgrade_only' WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()


def get_summary(telegram_id: int) -> str | None:
    """Retrieve the saved Mt. Everest summary."""
    conn = get_connection()
    row = conn.execute(
        "SELECT summary FROM mt_everest_sessions WHERE telegram_id = ?",
        (telegram_id,)
    ).fetchone()
    conn.close()
    return row["summary"] if row else None


def mark_email_sent(telegram_id: int):
    """Mark that the summary email has been sent."""
    conn = get_connection()
    conn.execute(
        "UPDATE mt_everest_sessions SET email_sent = 1 WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()


# ---- Conversation persistence ----

def save_message(telegram_id: int, role: str, content: str):
    """Save a single message to the database."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO messages (telegram_id, role, content) VALUES (?, ?, ?)",
        (telegram_id, role, content),
    )
    conn.commit()
    conn.close()


def load_conversation(telegram_id: int, limit: int = 20) -> list[dict]:
    """Load the most recent messages for a user.

    Returns list of {"role": "user"/"assistant", "content": "..."} dicts,
    ordered oldest-first (ready for prompt construction).
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE telegram_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (telegram_id, limit),
    ).fetchall()
    conn.close()
    # Reverse so oldest is first
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


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


# ---- Follow-up scheduling ----

def get_pending_followups(day_offset: int, followup_column: str) -> list[dict]:
    """Get sessions that need a follow-up at the given day offset.

    Args:
        day_offset: Days after completion (1, 3, 5, or 7).
        followup_column: DB column name (e.g. 'followup_1d_sent').

    Returns list of dicts with telegram_id, email, summary, completed_at.
    """
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT s.telegram_id, u.email, s.summary, s.completed_at
        FROM mt_everest_sessions s
        JOIN users u ON s.telegram_id = u.telegram_id
        WHERE s.status IN ('completed', 'upgrade_only')
          AND s.completed_at IS NOT NULL
          AND s.{followup_column} = 0
          AND datetime(s.completed_at, '+{day_offset} days') <= datetime('now')
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_followup_sent(telegram_id: int, followup_column: str):
    """Mark a follow-up as sent for a user."""
    conn = get_connection()
    conn.execute(
        f"UPDATE mt_everest_sessions SET {followup_column} = 1 WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()


def get_bridge_data(email: str) -> dict | None:
    """Retrieve Mt. Everest summary for the Core → Pro bridge.

    Returns dict with summary + milestones, or None if not found.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT s.summary, s.completed_at, u.email
        FROM mt_everest_sessions s
        JOIN users u ON s.telegram_id = u.telegram_id
        WHERE u.email = ? AND s.status IN ('completed', 'upgrade_only')
    """, (email.strip().lower(),)).fetchone()
    conn.close()

    if not row or not row["summary"]:
        return None

    return {
        "email": row["email"],
        "summary": row["summary"],
        "completed_at": row["completed_at"],
    }


def migrate_followup_columns():
    """Add follow-up columns to existing databases (safe to run multiple times)."""
    conn = get_connection()
    columns = [
        ("followup_1d_sent", "INTEGER DEFAULT 0"),
        ("followup_3d_sent", "INTEGER DEFAULT 0"),
        ("followup_5d_sent", "INTEGER DEFAULT 0"),
        ("followup_7d_email_sent", "INTEGER DEFAULT 0"),
    ]
    for col_name, col_type in columns:
        try:
            conn.execute(
                f"ALTER TABLE mt_everest_sessions ADD COLUMN {col_name} {col_type}"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()
