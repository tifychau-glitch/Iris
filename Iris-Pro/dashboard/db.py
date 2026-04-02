"""Database setup and helpers for the project dashboard."""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "projects.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
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
    """)
    conn.commit()
    conn.close()


# --- Helper functions for Claude scripts ---

def add_project(name, description="", status="idea"):
    conn = get_db()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO projects (name, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (name, description, status, now, now),
    )
    project_id = cur.lastrowid
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, f"Project created with status: {status}", now),
    )
    conn.commit()
    conn.close()
    return project_id


def update_status(project_id, new_status):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, project_id),
    )
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, f"Status changed to: {new_status}", now),
    )
    conn.commit()
    conn.close()


def add_task(project_id, title):
    conn = get_db()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, done, created_at) VALUES (?, ?, 0, ?)",
        (project_id, title, now),
    )
    task_id = cur.lastrowid
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?",
        (now, project_id),
    )
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, f"Task added: {title}", now),
    )
    conn.commit()
    conn.close()
    return task_id


def complete_task(task_id):
    conn = get_db()
    now = datetime.now().isoformat()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return
    new_done = 0 if task["done"] else 1
    conn.execute(
        "UPDATE tasks SET done = ?, completed_at = ? WHERE id = ?",
        (new_done, now if new_done else None, task_id),
    )
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?",
        (now, task["project_id"]),
    )
    status_word = "completed" if new_done else "reopened"
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (task["project_id"], f"Task {status_word}: {task['title']}", now),
    )
    conn.commit()
    conn.close()


def log_activity(project_id, message):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?",
        (now, project_id),
    )
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, message, now),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
