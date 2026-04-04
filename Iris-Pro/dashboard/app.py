"""Project Dashboard - Simple local Flask server."""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from db import get_db, init_db

app = Flask(__name__, static_folder=".", static_url_path="")

ACCOUNTABILITY_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "iris_accountability.db")


def get_accountability_db():
    if not os.path.exists(ACCOUNTABILITY_DB):
        return None
    conn = sqlite3.connect(ACCOUNTABILITY_DB)
    conn.row_factory = sqlite3.Row
    return conn

VALID_STATUSES = ["idea", "not_started", "in_progress", "blocked", "done"]


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# --- API ---

@app.route("/api/projects", methods=["GET"])
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
def get_activity(project_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity WHERE project_id = ? ORDER BY created_at DESC LIMIT 50",
        (project_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects/<int:project_id>/activity", methods=["POST"])
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
def list_tasks(project_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY done ASC, created_at ASC",
        (project_id,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects/<int:project_id>/tasks", methods=["POST"])
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


if __name__ == "__main__":
    init_db()
    print("\n  Dashboard running at: http://localhost:5050\n")
    app.run(host="127.0.0.1", port=5050, debug=False)
