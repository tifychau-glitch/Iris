"""
Tool: Goal Decay Tracker
Purpose: Silently track goals the user shares and surface ONE stale goal at a time
         when it has gone quiet for its timeframe-specific decay window.
Usage: python3 scripts/goal_decay.py <command> [options]

Commands:
  capture       Capture a new goal (silent)
  find          Find existing goals matching a query (for dedup before capture)
  touch         Reset last_touched on an existing goal
  check_stale   Return at most ONE stale goal to surface (respects session scope)
  archive       Archive a goal (still alive=no, let it go)
  list          List goals (user-initiated only)

Principles:
  - Silent capture. Never announce.
  - One stale goal per conversation. Session-scoped.
  - Decay by timeframe: short=7d, medium=21d, long=45d.
  - After 3 re-stales with no genuine touches, stop auto-surfacing.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "goals.db"
SESSION_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / ".goal_decay_session.json"

DECAY_WINDOWS = {
    "short": 7,
    "medium": 21,
    "long": 45,
}

SESSION_TIMEOUT_HOURS = 6
MAX_RESURFACE_COUNT = 3


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_text TEXT NOT NULL,
            timeframe TEXT NOT NULL CHECK(timeframe IN ('short','medium','long')),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
            created_at TEXT NOT NULL,
            last_touched TEXT NOT NULL,
            surfaced_count INTEGER NOT NULL DEFAULT 0,
            last_surfaced_at TEXT,
            archived_reason TEXT
        )
    """)
    conn.commit()
    return conn


def load_session():
    if not SESSION_PATH.exists():
        return {"last_active": None, "surfaced_ids": []}
    try:
        data = json.loads(SESSION_PATH.read_text())
        last = data.get("last_active")
        if last:
            last_dt = datetime.fromisoformat(last)
            if datetime.now() - last_dt > timedelta(hours=SESSION_TIMEOUT_HOURS):
                return {"last_active": None, "surfaced_ids": []}
        return data
    except Exception:
        return {"last_active": None, "surfaced_ids": []}


def save_session(session):
    session["last_active"] = datetime.now().isoformat()
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(session))


def capture_goal(title, original_text, timeframe):
    if timeframe not in DECAY_WINDOWS:
        timeframe = "medium"

    conn = init_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute(
        """
        INSERT INTO goals (title, original_text, timeframe, status, created_at, last_touched)
        VALUES (?, ?, ?, 'active', ?, ?)
        """,
        (title, original_text, timeframe, now, now),
    )
    goal_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "captured": True,
        "id": goal_id,
        "title": title,
        "timeframe": timeframe,
        "decay_days": DECAY_WINDOWS[timeframe],
    }


def find_goals(query):
    conn = init_db()
    cur = conn.cursor()
    like = f"%{query.lower()}%"
    cur.execute(
        """
        SELECT * FROM goals
        WHERE status = 'active'
        AND (LOWER(title) LIKE ? OR LOWER(original_text) LIKE ?)
        ORDER BY last_touched DESC
        """,
        (like, like),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"query": query, "matches": rows}


def touch_goal(goal_id):
    conn = init_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        "UPDATE goals SET last_touched = ?, surfaced_count = 0 WHERE id = ? AND status = 'active'",
        (now, goal_id),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"touched": updated > 0, "id": goal_id}


def check_stale():
    conn = init_db()
    cur = conn.cursor()
    session = load_session()
    surfaced_this_session = set(session.get("surfaced_ids", []))

    cur.execute(
        "SELECT * FROM goals WHERE status = 'active' ORDER BY last_touched ASC"
    )
    goals = cur.fetchall()

    now = datetime.now()
    stale_candidates = []

    for g in goals:
        if g["id"] in surfaced_this_session:
            continue
        if g["surfaced_count"] >= MAX_RESURFACE_COUNT:
            continue

        decay_days = DECAY_WINDOWS[g["timeframe"]]
        last_touched = datetime.fromisoformat(g["last_touched"])
        days_quiet = (now - last_touched).days

        if days_quiet >= decay_days:
            stale_candidates.append({
                "id": g["id"],
                "title": g["title"],
                "original_text": g["original_text"],
                "timeframe": g["timeframe"],
                "days_quiet": days_quiet,
                "decay_window": decay_days,
                "resurface_count": g["surfaced_count"],
                "last_touched": g["last_touched"],
            })

    conn.close()

    if not stale_candidates:
        return {"stale": None, "reason": "no stale goals (or all already surfaced this session)"}

    # Pick the one that's been quiet the longest
    stale_candidates.sort(key=lambda x: x["days_quiet"], reverse=True)
    chosen = stale_candidates[0]

    # Mark as surfaced
    conn = init_db()
    cur = conn.cursor()
    now_iso = now.isoformat()
    cur.execute(
        """
        UPDATE goals
        SET surfaced_count = surfaced_count + 1, last_surfaced_at = ?
        WHERE id = ?
        """,
        (now_iso, chosen["id"]),
    )
    conn.commit()
    conn.close()

    surfaced_this_session.add(chosen["id"])
    session["surfaced_ids"] = list(surfaced_this_session)
    save_session(session)

    chosen["resurface_count"] += 1
    chosen["is_resurface"] = chosen["resurface_count"] > 1
    return {"stale": chosen}


def archive_goal(goal_id, reason):
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE goals SET status = 'archived', archived_reason = ? WHERE id = ?",
        (reason, goal_id),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"archived": updated > 0, "id": goal_id, "reason": reason}


def list_goals(status):
    conn = init_db()
    cur = conn.cursor()
    if status == "all":
        cur.execute("SELECT * FROM goals ORDER BY last_touched DESC")
    else:
        cur.execute("SELECT * FROM goals WHERE status = ? ORDER BY last_touched DESC", (status,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"status": status, "count": len(rows), "goals": rows}


def main():
    parser = argparse.ArgumentParser(description="Goal Decay Tracker — silent capture, stale surfacing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cap = sub.add_parser("capture", help="Capture a new goal")
    p_cap.add_argument("--title", required=True)
    p_cap.add_argument("--original-text", required=True)
    p_cap.add_argument("--timeframe", default="medium", choices=list(DECAY_WINDOWS.keys()))

    p_find = sub.add_parser("find", help="Search existing goals")
    p_find.add_argument("--query", required=True)

    p_touch = sub.add_parser("touch", help="Reset decay on a goal")
    p_touch.add_argument("--id", type=int, required=True)

    sub.add_parser("check_stale", help="Return one stale goal to surface, if any")

    p_arch = sub.add_parser("archive", help="Archive a goal")
    p_arch.add_argument("--id", type=int, required=True)
    p_arch.add_argument("--reason", default="user let it go")

    p_list = sub.add_parser("list", help="List goals")
    p_list.add_argument("--status", default="active", choices=["active", "archived", "all"])

    args = parser.parse_args()

    if args.command == "capture":
        result = capture_goal(args.title, args.original_text, args.timeframe)
    elif args.command == "find":
        result = find_goals(args.query)
    elif args.command == "touch":
        result = touch_goal(args.id)
    elif args.command == "check_stale":
        result = check_stale()
    elif args.command == "archive":
        result = archive_goal(args.id, args.reason)
    elif args.command == "list":
        result = list_goals(args.status)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
