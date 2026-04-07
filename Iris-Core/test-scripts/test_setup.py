"""
IRIS Core -- Test Setup & Helpers
Initialize test database and provide utility functions for testing.
"""

import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import iris modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import config

# Use test database
TEST_DB_PATH = Path(__file__).parent.parent / "data" / "iris_core_test.db"


def get_test_db():
    """Get a connection to the test database."""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_test_db():
    """Initialize test database with schema."""
    conn = get_test_db()
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(telegram_id) REFERENCES users(telegram_id)
        );
    """)
    conn.commit()
    conn.close()


def create_test_user(telegram_id=123456789, email="test@example.com"):
    """Create a test user."""
    conn = get_test_db()
    conn.execute(
        "INSERT OR REPLACE INTO users (telegram_id, email) VALUES (?, ?)",
        (telegram_id, email)
    )
    conn.commit()
    conn.close()
    return telegram_id


def create_test_session(telegram_id=123456789):
    """Create a test Mt. Everest session."""
    conn = get_test_db()
    conn.execute(
        "INSERT OR REPLACE INTO mt_everest_sessions (telegram_id, status) VALUES (?, 'excavating')",
        (telegram_id,)
    )
    conn.commit()
    conn.close()


def save_test_message(telegram_id, role, content):
    """Save a test message to conversation history."""
    conn = get_test_db()
    conn.execute(
        "INSERT INTO messages (telegram_id, role, content) VALUES (?, ?, ?)",
        (telegram_id, role, content)
    )
    conn.commit()
    conn.close()


def get_test_session(telegram_id=123456789):
    """Get a test session."""
    conn = get_test_db()
    cursor = conn.execute(
        "SELECT * FROM mt_everest_sessions WHERE telegram_id = ?",
        (telegram_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_test_summary(telegram_id, summary):
    """Save a summary to test session."""
    conn = get_test_db()
    conn.execute(
        "UPDATE mt_everest_sessions SET summary = ?, status = 'completed' WHERE telegram_id = ?",
        (summary, telegram_id)
    )
    conn.commit()
    conn.close()


def reset_test_db():
    """Delete and reinitialize test database."""
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    init_test_db()


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_section(text):
    """Print a formatted section."""
    print(f"\n--- {text} ---\n")


def print_success(text):
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text):
    """Print an error message."""
    print(f"✗ {text}")


def print_info(text):
    """Print an info message."""
    print(f"• {text}")


if __name__ == "__main__":
    print("Initializing test database...")
    reset_test_db()
    print("✓ Test database ready at:", TEST_DB_PATH)
