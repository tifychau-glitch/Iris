"""
Tool: Friction Log
Purpose: Silently capture friction (reasons things don't happen) and surface
         patterns only when the same category appears 3+ times in 30 days.
Usage: python3 scripts/friction_log.py <command> [options]

Commands:
  log          Log a friction entry (returns pattern info + should_surface)
  list         List recent friction entries
  patterns     Show all categories with 3+ occurrences in the last 30 days
  remove       Remove a misclassified entry by id
  mark_surfaced  Mark a category's current pattern as surfaced (called internally)

Principles:
  - Capture is silent. Never announce logging to the user.
  - Surface only when count >= 3 in the last 30 days, and only the first time.
  - Friction older than 60 days is excluded from pattern counts (decay).
  - A surfaced pattern can re-surface if it goes quiet 14+ days and returns.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "friction_log.db"

VALID_CATEGORIES = {
    "interruption",
    "energy",
    "focus",
    "time",
    "blocked_external",
    "environment",
    "distraction",
    "caregiving",
    "scope_unclear",
    "avoidance",
    "email_overwhelm",
    "shiny_object",
    "other",
}

SURFACE_THRESHOLD = 3
PATTERN_WINDOW_DAYS = 30
DECAY_DAYS = 60
REVIVAL_QUIET_DAYS = 14


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            thing TEXT,
            friction_text TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS surfaced_patterns (
            category TEXT PRIMARY KEY,
            surfaced_at TEXT NOT NULL,
            count_at_surface INTEGER NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_friction_timestamp ON friction_log(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_friction_category ON friction_log(category)")
    conn.commit()
    return conn


def log_friction(thing, friction_text, category):
    if category not in VALID_CATEGORIES:
        category = "other"

    conn = init_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute(
        "INSERT INTO friction_log (timestamp, thing, friction_text, category) VALUES (?, ?, ?, ?)",
        (now, thing, friction_text, category),
    )
    entry_id = cur.lastrowid
    conn.commit()

    pattern_info = check_pattern(conn, category)

    should_surface = False
    if pattern_info["count"] >= SURFACE_THRESHOLD:
        surfaced = get_surfaced(conn, category)
        if surfaced is None:
            should_surface = True
        else:
            # Revival: was surfaced before, then quiet for 14+ days, now back
            last_before_current = get_prior_entry_before(conn, category, entry_id)
            if last_before_current:
                last_dt = datetime.fromisoformat(last_before_current["timestamp"])
                gap = datetime.now() - last_dt
                if gap.days >= REVIVAL_QUIET_DAYS:
                    should_surface = True

    if should_surface:
        mark_surfaced(conn, category, pattern_info["count"])

    conn.close()

    return {
        "logged": True,
        "id": entry_id,
        "category": category,
        "should_surface": should_surface,
        "pattern": pattern_info if pattern_info["count"] >= SURFACE_THRESHOLD else None,
    }


def check_pattern(conn, category):
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=PATTERN_WINDOW_DAYS)).isoformat()

    cur.execute(
        """
        SELECT friction_text, timestamp
        FROM friction_log
        WHERE category = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        """,
        (category, cutoff),
    )
    rows = cur.fetchall()

    if not rows:
        return {"category": category, "count": 0}

    examples = [r["friction_text"] for r in rows[:5]]
    return {
        "category": category,
        "count": len(rows),
        "recent_examples": examples,
        "first_seen": rows[-1]["timestamp"][:10],
        "latest": rows[0]["timestamp"][:10],
    }


def get_surfaced(conn, category):
    cur = conn.cursor()
    cur.execute("SELECT * FROM surfaced_patterns WHERE category = ?", (category,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_prior_entry_before(conn, category, current_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM friction_log
        WHERE category = ? AND id < ?
        ORDER BY id DESC LIMIT 1
        """,
        (category, current_id),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def mark_surfaced(conn, category, count):
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO surfaced_patterns (category, surfaced_at, count_at_surface)
        VALUES (?, ?, ?)
        ON CONFLICT(category) DO UPDATE SET
            surfaced_at = excluded.surfaced_at,
            count_at_surface = excluded.count_at_surface
        """,
        (category, now, count),
    )
    conn.commit()


def list_friction(days):
    conn = init_db()
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT * FROM friction_log WHERE timestamp >= ? ORDER BY timestamp DESC",
        (cutoff,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"days": days, "count": len(rows), "entries": rows}


def all_patterns():
    conn = init_db()
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=PATTERN_WINDOW_DAYS)).isoformat()
    cur.execute(
        """
        SELECT category, COUNT(*) as count
        FROM friction_log
        WHERE timestamp >= ?
        GROUP BY category
        HAVING count >= ?
        ORDER BY count DESC
        """,
        (cutoff, SURFACE_THRESHOLD),
    )
    patterns = []
    for row in cur.fetchall():
        surfaced = get_surfaced(conn, row["category"])
        patterns.append({
            "category": row["category"],
            "count": row["count"],
            "surfaced": surfaced is not None,
            "surfaced_at": surfaced["surfaced_at"] if surfaced else None,
        })
    conn.close()
    return {"patterns": patterns, "window_days": PATTERN_WINDOW_DAYS}


def remove_entry(entry_id):
    conn = init_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM friction_log WHERE id = ?", (entry_id,))
    removed = cur.rowcount
    conn.commit()
    conn.close()
    return {"removed": removed > 0, "id": entry_id}


def main():
    parser = argparse.ArgumentParser(description="Friction Log — silent capture, pattern-aware surfacing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log", help="Log a friction entry")
    p_log.add_argument("--thing", default="", help="What didn't happen (e.g. 'newsletter')")
    p_log.add_argument("--friction-text", required=True, help="The user's own words")
    p_log.add_argument("--category", required=True, help=f"One of: {sorted(VALID_CATEGORIES)}")

    p_list = sub.add_parser("list", help="List recent friction entries")
    p_list.add_argument("--days", type=int, default=30)

    sub.add_parser("patterns", help="Show active patterns (3+ in 30 days)")

    p_rm = sub.add_parser("remove", help="Remove a misclassified entry")
    p_rm.add_argument("--id", type=int, required=True)

    args = parser.parse_args()

    if args.command == "log":
        result = log_friction(args.thing, args.friction_text, args.category)
    elif args.command == "list":
        result = list_friction(args.days)
    elif args.command == "patterns":
        result = all_patterns()
    elif args.command == "remove":
        result = remove_entry(args.id)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
