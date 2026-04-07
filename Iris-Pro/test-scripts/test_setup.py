"""
IRIS Pro -- Test Setup & Helpers
Initialize test database and provide utility functions for testing.
"""

import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Test database paths
TEST_PROJECTS_DB = Path(__file__).parent.parent / "data" / "projects_test.db"
TEST_ACCOUNTABILITY_DB = Path(__file__).parent.parent / "data" / "iris_accountability_test.db"
TEST_TASKS_DB = Path(__file__).parent.parent / "data" / "tasks_test.db"


def get_projects_db():
    """Get connection to test projects database."""
    TEST_PROJECTS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TEST_PROJECTS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_accountability_db():
    """Get connection to test accountability database."""
    TEST_ACCOUNTABILITY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TEST_ACCOUNTABILITY_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_tasks_db():
    """Get connection to test tasks database."""
    TEST_TASKS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TEST_TASKS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_test_databases():
    """Initialize all test databases with schema."""
    # Projects DB
    conn = get_projects_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'idea',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'disconnected',
            config_json TEXT DEFAULT '{}',
            last_verified TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    # Accountability DB
    conn = get_accountability_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_active TEXT,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            commitment TEXT NOT NULL,
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
    """)
    conn.commit()
    conn.close()

    # Tasks DB
    conn = get_tasks_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def reset_test_databases():
    """Delete and reinitialize all test databases."""
    for db_path in [TEST_PROJECTS_DB, TEST_ACCOUNTABILITY_DB, TEST_TASKS_DB]:
        if db_path.exists():
            db_path.unlink()
    init_test_databases()


def create_test_user(user_id="test-user-001", email="test@example.com"):
    """Create a test user."""
    conn = get_accountability_db()
    conn.execute(
        """INSERT OR REPLACE INTO users (user_id, email, created_at, status)
           VALUES (?, ?, ?, 'active')""",
        (user_id, email, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return user_id


def create_test_project(name="Test Project", description="", status="not_started"):
    """Create a test project."""
    conn = get_projects_db()
    now = datetime.now().isoformat()
    cursor = conn.execute(
        """INSERT INTO projects (name, description, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (name, description, status, now, now)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id


def create_test_commitment(user_id, commitment_text, due_date=None):
    """Create a test commitment."""
    if due_date is None:
        due_date = (datetime.now() + timedelta(days=7)).isoformat()

    conn = get_accountability_db()
    cursor = conn.execute(
        """INSERT INTO commitments (user_id, commitment, due_date, status, created_at)
           VALUES (?, ?, ?, 'pending', ?)""",
        (user_id, commitment_text, due_date, datetime.now().isoformat())
    )
    commitment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return commitment_id


def get_project(project_id):
    """Get a project by ID."""
    conn = get_projects_db()
    cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_commitments(user_id):
    """Get all commitments for a user."""
    conn = get_accountability_db()
    cursor = conn.execute(
        "SELECT * FROM commitments WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---- Output Helpers ----

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


def print_warning(text):
    """Print a warning message."""
    print(f"⚠ {text}")


if __name__ == "__main__":
    print("Initializing test databases...")
    reset_test_databases()
    print("✓ Test databases ready:")
    print(f"  - {TEST_PROJECTS_DB}")
    print(f"  - {TEST_ACCOUNTABILITY_DB}")
    print(f"  - {TEST_TASKS_DB}")
