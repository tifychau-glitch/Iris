"""IRIS Settings Dashboard - Local Flask server for connector management."""

import json
import os
import subprocess
import sys
try:
    import yaml
except ImportError:
    yaml = None
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, redirect
from db import get_db, init_db

app = Flask(__name__, static_folder=".", static_url_path="")

DASHBOARD_DIR = Path(__file__).parent
PROJECT_ROOT = DASHBOARD_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
CONNECTORS_YAML = DASHBOARD_DIR / "connectors.yaml"


# --- Cross-platform file locking ---

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


@app.route("/")
def index():
    return send_from_directory(".", "settings.html")


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
def settings_page():
    return redirect("/")


# --- Connectors ---

@app.route("/api/connectors", methods=["GET"])

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
        r["status_only"] = reg.get("status_only", False)

        # Check which fields have values in .env (don't expose the actual values)
        fields_status = {}
        for field in r["fields"]:
            val = read_env_value(field["key"])
            fields_status[field["key"]] = bool(val)
        r["fields_configured"] = fields_status

        # status_only connectors are always shown as connected
        if r.get("status_only"):
            r["status"] = "connected"

        # Don't send config_json to frontend (may contain sensitive data)
        r.pop("config_json", None)
        result.append(r)

    return jsonify(result)


@app.route("/api/connectors/<name>/save", methods=["POST"])

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

def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return jsonify({r["key"]: r["value"] for r in rows})


@app.route("/api/settings/<key>", methods=["PUT"])

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

def system_status():
    """System health overview."""
    conn = get_db()

    connected = conn.execute(
        "SELECT COUNT(*) FROM connectors WHERE status = 'connected'"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM connectors").fetchone()[0]
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
