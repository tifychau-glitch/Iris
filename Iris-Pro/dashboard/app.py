"""Project Dashboard - Simple local Flask server with connector management."""

import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import sys
from functools import wraps
try:
    import yaml
except ImportError:
    yaml = None
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, redirect, session, make_response
from db import get_db, init_db

app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(hours=24)

DASHBOARD_DIR = Path(__file__).parent
PROJECT_ROOT = DASHBOARD_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
CONNECTORS_YAML = DASHBOARD_DIR / "connectors.yaml"
ACCOUNTABILITY_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "iris_accountability.db")


def get_accountability_db():
    if not os.path.exists(ACCOUNTABILITY_DB):
        return None
    conn = sqlite3.connect(ACCOUNTABILITY_DB)
    conn.row_factory = sqlite3.Row
    return conn

VALID_STATUSES = ["idea", "not_started", "in_progress", "blocked", "done"]


# --- Cross-platform file locking ---

from contextlib import contextmanager

@contextmanager
def _file_lock(lock_path):
    """Acquire an exclusive file lock (cross-platform)."""
    f = open(lock_path, "w")
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        yield f
    finally:
        f.close()


# --- Auth ---

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash a password with PBKDF2-SHA256. Returns (hash, salt)."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return hashed, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against stored hash. Supports both PBKDF2 and legacy SHA-256."""
    # Try PBKDF2 first (new format)
    pbkdf2_hash, _ = hash_password(password, salt)
    if pbkdf2_hash == stored_hash:
        return True
    # Fallback: legacy SHA-256 for existing installs
    legacy_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return legacy_hash == stored_hash


def is_setup_complete() -> bool:
    """Check if initial account setup has been done."""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) FROM settings WHERE key = 'auth_hash'").fetchone()
    conn.close()
    return row[0] > 0


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_setup_complete():
            # No password set yet — redirect to setup (not open access)
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Setup required. Go to /setup"}), 401
            return redirect("/setup")
        if not session.get("authenticated"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated


@app.route("/login")
def login_page():
    if not is_setup_complete():
        return redirect("/setup")
    return send_from_directory(".", "login.html")


@app.route("/setup")
def setup_page():
    if is_setup_complete():
        return redirect("/login")
    return send_from_directory(".", "setup-auth.html")


@app.route("/api/auth/setup", methods=["POST"])
def auth_setup():
    """First-time password setup."""
    if is_setup_complete():
        return jsonify({"error": "Already configured"}), 400

    data = request.json
    password = data.get("password", "").strip()
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    hashed, salt = hash_password(password)
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('auth_hash', ?, ?)",
        (hashed, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('auth_salt', ?, ?)",
        (salt, now),
    )
    conn.commit()
    conn.close()

    session["authenticated"] = True
    session.permanent = True
    return jsonify({"success": True})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate with password."""
    data = request.json
    password = data.get("password", "").strip()

    conn = get_db()
    hash_row = conn.execute("SELECT value FROM settings WHERE key = 'auth_hash'").fetchone()
    salt_row = conn.execute("SELECT value FROM settings WHERE key = 'auth_salt'").fetchone()
    conn.close()

    if not hash_row or not salt_row:
        return jsonify({"error": "No account configured"}), 400

    if verify_password(password, hash_row["value"], salt_row["value"]):
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"success": True})

    return jsonify({"error": "Wrong password"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/change-password", methods=["POST"])
@login_required
def auth_change_password():
    data = request.get_json()
    current = data.get("current_password", "")
    new_pw = data.get("new_password", "")

    if not current or not new_pw:
        return jsonify({"success": False, "error": "Both fields required."})

    if len(new_pw) < 6:
        return jsonify({"success": False, "error": "New password must be at least 6 characters."})

    conn = get_db()
    row_hash = conn.execute("SELECT value FROM settings WHERE key = 'auth_hash'").fetchone()
    row_salt = conn.execute("SELECT value FROM settings WHERE key = 'auth_salt'").fetchone()

    if not row_hash or not row_salt:
        conn.close()
        return jsonify({"success": False, "error": "No password set."})

    if not verify_password(current, row_hash[0], row_salt[0]):
        conn.close()
        return jsonify({"success": False, "error": "Current password is incorrect."})

    new_hash, new_salt = hash_password(new_pw)
    now = datetime.now().isoformat()
    conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'auth_hash'", (new_hash, now))
    conn.execute("UPDATE settings SET value = ?, updated_at = ? WHERE key = 'auth_salt'", (new_salt, now))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route("/")
@login_required
def index():
    return send_from_directory(".", "index.html")


# --- API ---

@app.route("/api/projects", methods=["GET"])
@login_required
def list_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE status != 'archived' ORDER BY updated_at DESC").fetchall()
    projects = [dict(r) for r in rows]
    # Attach task counts to each project
    for p in projects:
        total = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id = ?", (p["id"],)).fetchone()[0]
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE project_id = ? AND done = 1", (p["id"],)).fetchone()[0]
        p["task_total"] = total
        p["task_done"] = done
    conn.close()
    return jsonify(projects)


@app.route("/api/projects", methods=["POST"])
@login_required
def create_project():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    description = data.get("description", "")
    status = data.get("status", "idea")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    now = datetime.now().isoformat()
    conn = get_db()
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
    project = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    conn.close()
    return jsonify(project), 201


@app.route("/api/projects/<int:project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    data = request.json
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    now = datetime.now().isoformat()
    updates = []
    params = []

    if "name" in data:
        updates.append("name = ?")
        params.append(data["name"])
    if "description" in data:
        updates.append("description = ?")
        params.append(data["description"])
    if "status" in data:
        if data["status"] not in VALID_STATUSES + ["archived"]:
            conn.close()
            return jsonify({"error": f"Invalid status"}), 400
        old_status = project["status"]
        updates.append("status = ?")
        params.append(data["status"])
        conn.execute(
            "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
            (project_id, f"Status: {old_status} -> {data['status']}", now),
        )

    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        params.append(project_id)
        conn.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    updated = dict(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())
    conn.close()
    return jsonify(updated)


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
@login_required
def archive_project(project_id):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute("UPDATE projects SET status = 'archived', updated_at = ? WHERE id = ?", (now, project_id))
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, "Project archived", now),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/projects/<int:project_id>/activity", methods=["GET"])
@login_required
def get_activity(project_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity WHERE project_id = ? ORDER BY created_at DESC LIMIT 50",
        (project_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects/<int:project_id>/activity", methods=["POST"])
@login_required
def add_activity(project_id):
    data = request.json
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    now = datetime.now().isoformat()
    conn = get_db()
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
    return jsonify({"ok": True}), 201


@app.route("/api/projects/<int:project_id>/tasks", methods=["GET"])
@login_required
def list_tasks(project_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY done ASC, created_at ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects/<int:project_id>/tasks", methods=["POST"])
@login_required
def create_task(project_id):
    data = request.json
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    now = datetime.now().isoformat()
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, done, created_at) VALUES (?, ?, 0, ?)",
        (project_id, title, now),
    )
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id)
    )
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (project_id, f"Task added: {title}", now),
    )
    conn.commit()
    task = dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404

    now = datetime.now().isoformat()
    new_done = 0 if task["done"] else 1
    conn.execute(
        "UPDATE tasks SET done = ?, completed_at = ? WHERE id = ?",
        (new_done, now if new_done else None, task_id),
    )
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?", (now, task["project_id"])
    )
    status_word = "completed" if new_done else "reopened"
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (task["project_id"], f"Task {status_word}: {task['title']}", now),
    )
    conn.commit()
    updated = dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())
    conn.close()
    return jsonify(updated)


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    conn = get_db()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return jsonify({"error": "Task not found"}), 404
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.execute(
        "INSERT INTO activity (project_id, message, created_at) VALUES (?, ?, ?)",
        (task["project_id"], f"Task removed: {task['title']}", now),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/accountability", methods=["GET"])
@login_required
def accountability_metrics():
    conn = get_accountability_db()
    if not conn:
        return jsonify({"available": False, "message": "No accountability data yet"})

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    # Self-trust score (14-day)
    made_14d = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ?", (two_weeks_ago,)
    ).fetchone()[0]
    kept_14d = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ? AND completed = 1", (two_weeks_ago,)
    ).fetchone()[0]
    trust_score = round(kept_14d / made_14d, 2) if made_14d > 0 else 0.0

    # This week: promises made vs kept
    made_week = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ?", (week_ago,)
    ).fetchone()[0]
    kept_week = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ? AND completed = 1", (week_ago,)
    ).fetchone()[0]
    broken_week = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ? AND skipped = 1", (week_ago,)
    ).fetchone()[0]

    # Current streak
    scores = conn.execute(
        "SELECT completion_rate FROM daily_scores ORDER BY date DESC LIMIT 30"
    ).fetchall()
    streak = 0
    for s in scores:
        if s["completion_rate"] >= 0.80:
            streak += 1
        else:
            break

    # Accountability level
    week_scores = conn.execute(
        "SELECT completion_rate FROM daily_scores WHERE date >= ?", (week_ago,)
    ).fetchall()
    rates = [r["completion_rate"] for r in week_scores]
    avg_rate = sum(rates) / len(rates) if rates else 0
    if avg_rate >= 0.80:
        level = 1
    elif avg_rate >= 0.60:
        level = 2
    elif avg_rate >= 0.40:
        level = 3
    elif avg_rate >= 0.20:
        level = 4
    else:
        level = 5

    level_names = {1: "Sweet Iris", 2: "Subtle Side-Eye", 3: "Passive Aggressive",
                   4: "Direct Confrontation", 5: "Full Drill Sergeant"}

    # Top excuse category
    excuse_row = conn.execute(
        """SELECT excuse_category, COUNT(*) as cnt FROM commitments
           WHERE due_date >= ? AND excuse_category IS NOT NULL
           GROUP BY excuse_category ORDER BY cnt DESC LIMIT 1""",
        (week_ago,)
    ).fetchone()
    top_excuse = excuse_row["excuse_category"] if excuse_row else None

    # Ghost days (days with no interaction in last 7)
    interaction_days = conn.execute(
        """SELECT COUNT(DISTINCT date(created_at)) FROM interactions
           WHERE created_at >= ?""",
        (week_ago,)
    ).fetchone()[0]
    ghost_days = 7 - interaction_days

    # Daily breakdown for chart (last 7 days)
    daily = conn.execute(
        "SELECT date, completion_rate, commitments_made, commitments_completed FROM daily_scores WHERE date >= ? ORDER BY date",
        (week_ago,)
    ).fetchall()
    daily_data = [dict(d) for d in daily]

    conn.close()
    return jsonify({
        "available": True,
        "self_trust_score": trust_score,
        "streak": streak,
        "accountability_level": level,
        "level_name": level_names.get(level, "Unknown"),
        "promises_made_week": made_week,
        "promises_kept_week": kept_week,
        "promises_broken_week": broken_week,
        "top_excuse": top_excuse,
        "ghost_days": ghost_days,
        "daily_data": daily_data,
    })


# --- Connector Registry ---

def load_connector_registry():
    """Load connector definitions from YAML."""
    if not CONNECTORS_YAML.exists():
        return []
    if yaml:
        with open(CONNECTORS_YAML) as f:
            return yaml.safe_load(f).get("connectors", [])
    # Fallback: parse simple YAML manually if pyyaml not installed
    # Install pyyaml for full support: pip install pyyaml
    return []


def read_env_value(key):
    """Read a single value from the .env file."""
    if not ENV_FILE.exists():
        return None
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                value = line[len(key) + 1:].strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                    # Unescape characters escaped by write_env_value
                    value = value.replace("\\$", "$").replace('\\"', '"').replace("\\\\", "\\")
                return value if value else None
    return None


def _escape_env_value(value):
    """Escape special chars inside double-quoted .env values."""
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    value = value.replace("$", "\\$")
    return value


def write_env_value(key, value):
    """Write or update a key in the .env file (file-locked)."""
    with _file_lock(str(ENV_FILE) + ".lock"):
        lines = []
        found = False
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                lines = f.readlines()

        escaped = _escape_env_value(value)
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f'{key}="{escaped}"\n')
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f'\n{key}="{escaped}"\n')

        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)


def remove_env_value(key):
    """Remove a key from the .env file (comments out the line, file-locked)."""
    if not ENV_FILE.exists():
        return
    with _file_lock(str(ENV_FILE) + ".lock"):
        with open(ENV_FILE) as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"# {line.strip()}\n")
            else:
                new_lines.append(line)
        with open(ENV_FILE, "w") as f:
            f.writelines(new_lines)


_connectors_yaml_mtime = 0.0


def sync_connectors_from_registry():
    """Ensure all connectors from YAML exist in the database."""
    global _connectors_yaml_mtime
    if CONNECTORS_YAML.exists():
        _connectors_yaml_mtime = CONNECTORS_YAML.stat().st_mtime

    registry = load_connector_registry()
    conn = get_db()
    now = datetime.now().isoformat()

    for c in registry:
        existing = conn.execute(
            "SELECT id FROM connectors WHERE name = ?", (c["name"],)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO connectors (name, display_name, category, status, config_json, created_at, updated_at)
                   VALUES (?, ?, ?, 'disconnected', '{}', ?, ?)""",
                (c["name"], c["display_name"], c["category"], now, now),
            )

    conn.commit()
    conn.close()


def _maybe_resync_connectors():
    """Re-sync if connectors.yaml has been modified since last check."""
    global _connectors_yaml_mtime
    if CONNECTORS_YAML.exists():
        current_mtime = CONNECTORS_YAML.stat().st_mtime
        if current_mtime > _connectors_yaml_mtime:
            sync_connectors_from_registry()


@app.route("/settings")
@login_required
def settings_page():
    return send_from_directory(".", "settings.html")


# --- Build Log ---

BUILD_LOG_PATH = PROJECT_ROOT / "IRIS-BUILD-LOG.md"


def _parse_build_log():
    """Parse IRIS-BUILD-LOG.md into structured entries."""
    if not BUILD_LOG_PATH.exists():
        return {"actions": [], "questions": []}

    text = BUILD_LOG_PATH.read_text()
    entries = {"actions": [], "questions": []}

    # Split on entry headers: "## [TYPE] DATE — TITLE"
    import re
    pattern = re.compile(r"^## \[(ACTION|QUESTION)\] (\d{4}-\d{2}-\d{2}) — (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, m in enumerate(matches):
        entry_type = m.group(1)
        date = m.group(2)
        title = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Stop body at next top-level section (## Actions / ## Questions)
        body = re.split(r"^---\s*$|^## (?!\[)", body, maxsplit=1, flags=re.MULTILINE)[0].strip()

        entry = {"date": date, "title": title, "body": body}
        if entry_type == "ACTION":
            entries["actions"].append(entry)
        else:
            entries["questions"].append(entry)

    return entries


@app.route("/build-log")
@login_required
def build_log_page():
    return send_from_directory(".", "build-log.html")


@app.route("/api/build-log", methods=["GET"])
@login_required
def build_log_api():
    return jsonify(_parse_build_log())


@app.route("/api/connectors", methods=["GET"])
@login_required
def list_connectors():
    """List all connectors with their status and registry info."""
    _maybe_resync_connectors()
    registry = load_connector_registry()
    registry_map = {c["name"]: c for c in registry}

    conn = get_db()
    rows = conn.execute("SELECT * FROM connectors ORDER BY name").fetchall()
    conn.close()

    result = []
    for row in rows:
        r = dict(row)
        reg = registry_map.get(r["name"], {})
        r["description"] = reg.get("description", "")
        r["category"] = reg.get("category", r.get("category", "other"))
        r["required"] = reg.get("required", False)
        r["fields"] = reg.get("fields", [])

        # Check which fields have values in .env (don't expose the actual values)
        fields_status = {}
        for field in r["fields"]:
            val = read_env_value(field["key"])
            fields_status[field["key"]] = bool(val)
        r["fields_configured"] = fields_status

        # Don't send config_json to frontend (may contain sensitive data)
        r.pop("config_json", None)
        result.append(r)

    return jsonify(result)


@app.route("/api/connectors/<name>/save", methods=["POST"])
@login_required
def save_connector(name):
    """Save connector credentials to .env file."""
    data = request.json
    registry = load_connector_registry()
    reg = next((c for c in registry if c["name"] == name), None)
    if not reg:
        return jsonify({"error": "Unknown connector"}), 404

    # Write each field to .env
    for field in reg.get("fields", []):
        key = field["key"]
        if key in data and data[key]:
            write_env_value(key, data[key])

    # Update connector status in DB
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "UPDATE connectors SET status = 'connected', updated_at = ? WHERE name = ?",
        (now, name),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route("/api/connectors/<name>/test", methods=["POST"])
@login_required
def test_connector(name):
    """Test a connector's credentials."""
    registry = load_connector_registry()
    reg = next((c for c in registry if c["name"] == name), None)
    if not reg:
        return jsonify({"success": False, "error": "Unknown connector"}), 404

    # Special case: Claude CLI — just check if it's installed
    if reg.get("test_command"):
        try:
            result = subprocess.run(
                reg["test_command"].split(),
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                now = datetime.now().isoformat()
                conn = get_db()
                conn.execute(
                    "UPDATE connectors SET status = 'connected', last_verified = ?, updated_at = ? WHERE name = ?",
                    (now, now, name),
                )
                conn.commit()
                conn.close()
                return jsonify({"success": True, "message": result.stdout.strip()})
            return jsonify({"success": False, "error": "CLI not found or not authenticated"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    # Run test script
    test_script = reg.get("test_script")
    if not test_script:
        return jsonify({"success": False, "error": "No test available"})

    script_path = DASHBOARD_DIR / "scripts" / test_script
    if not script_path.exists():
        return jsonify({"success": False, "error": f"Test script not found: {test_script}"})

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "DOTENV_PATH": str(ENV_FILE)},
        )
        output = json.loads(result.stdout) if result.stdout.strip() else {}

        if output.get("success"):
            now = datetime.now().isoformat()
            conn = get_db()
            conn.execute(
                "UPDATE connectors SET status = 'connected', last_verified = ?, updated_at = ? WHERE name = ?",
                (now, now, name),
            )
            conn.commit()
            conn.close()

        return jsonify(output)
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Test timed out"})
    except (json.JSONDecodeError, Exception) as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/connectors/<name>/disconnect", methods=["POST"])
@login_required
def disconnect_connector(name):
    """Mark a connector as disconnected and remove credentials from .env."""
    # Remove credential values from .env
    registry = load_connector_registry()
    reg = next((c for c in registry if c["name"] == name), None)
    if reg:
        for field in reg.get("fields", []):
            remove_env_value(field["key"])

    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "UPDATE connectors SET status = 'disconnected', updated_at = ? WHERE name = ?",
        (now, name),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return jsonify({r["key"]: r["value"] for r in rows})


@app.route("/api/settings/<key>", methods=["PUT"])
@login_required
def update_setting(key):
    data = request.json
    value = data.get("value", "")
    now = datetime.now().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, now),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/status", methods=["GET"])
@login_required
def system_status():
    """System health overview."""
    registry = load_connector_registry()
    conn = get_db()

    connected = conn.execute(
        "SELECT COUNT(*) FROM connectors WHERE status = 'connected'"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM connectors").fetchone()[0]

    # Count projects
    active_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status IN ('in_progress', 'not_started')"
    ).fetchone()[0]

    conn.close()

    # Check Claude CLI
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5
        )
        claude_ok = result.returncode == 0
        claude_version = result.stdout.strip() if claude_ok else None
    except Exception:
        claude_ok = False
        claude_version = None

    return jsonify({
        "connectors_connected": connected,
        "connectors_total": total,
        "active_projects": active_projects,
        "claude_cli": claude_ok,
        "claude_version": claude_version,
    })


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"\n  ERROR: Database initialization failed: {e}", file=sys.stderr)
        print("  Check file permissions for the data/ directory.", file=sys.stderr)
        sys.exit(1)
    sync_connectors_from_registry()
    print("\n  Dashboard running at: http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
