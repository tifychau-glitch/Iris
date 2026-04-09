"""
Tool: Energy Mapping
Purpose: Silently log when the user reports shipping things, then map their
         actual productive windows over time. Surface ONE insight on demand
         or once per 14 days when a clear pattern emerges.
Usage: python3 scripts/energy_mapping.py <command> [options]

Commands:
  log            Log a shipped event (silent)
  check_insight  Return one insight to surface, if any
  summary        Full pattern breakdown (user-initiated)
  list           List recent events

Principles:
  - Silent capture
  - Insights only at 15+ events with a clear pattern (>=40% in one bucket)
  - One insight per session, max one every 14 days per pattern
  - No external data — only what the user reports
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "energy_events.db"
SESSION_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / ".energy_mapping_session.json"

MIN_EVENTS_FOR_INSIGHT = 15
PATTERN_DOMINANCE_THRESHOLD = 0.40  # 40% of events in one bucket
INSIGHT_COOLDOWN_DAYS = 14
SESSION_TIMEOUT_HOURS = 6

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS energy_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            what TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            hour_of_day INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS surfaced_insights (
            insight_key TEXT PRIMARY KEY,
            surfaced_at TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def load_session():
    if not SESSION_PATH.exists():
        return {"last_active": None, "surfaced_keys": []}
    try:
        data = json.loads(SESSION_PATH.read_text())
        last = data.get("last_active")
        if last:
            last_dt = datetime.fromisoformat(last)
            if datetime.now() - last_dt > timedelta(hours=SESSION_TIMEOUT_HOURS):
                return {"last_active": None, "surfaced_keys": []}
        return data
    except Exception:
        return {"last_active": None, "surfaced_keys": []}


def save_session(session):
    session["last_active"] = datetime.now().isoformat()
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(session))


def log_event(what, category):
    conn = init_db()
    cur = conn.cursor()
    now = datetime.now()
    cur.execute(
        """
        INSERT INTO energy_events (timestamp, what, category, hour_of_day, day_of_week)
        VALUES (?, ?, ?, ?, ?)
        """,
        (now.isoformat(), what, category, now.hour, now.weekday()),
    )
    event_id = cur.lastrowid
    cur.execute("SELECT COUNT(*) as c FROM energy_events")
    total = cur.fetchone()["c"]
    conn.commit()
    conn.close()

    return {
        "logged": True,
        "id": event_id,
        "timestamp": now.isoformat(),
        "category": category,
        "total_events": total,
        "threshold_crossed": total == MIN_EVENTS_FOR_INSIGHT,
    }


def _hour_bucket(hour):
    """Group hours into 4 buckets: early morning, morning, afternoon, evening."""
    if 5 <= hour < 9:
        return "early morning (5-9am)"
    if 9 <= hour < 12:
        return "morning (9am-noon)"
    if 12 <= hour < 17:
        return "afternoon (noon-5pm)"
    if 17 <= hour < 21:
        return "evening (5-9pm)"
    return "late night (9pm-5am)"


def _compute_patterns():
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM energy_events")
    events = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not events:
        return None

    total = len(events)

    hour_buckets = Counter(_hour_bucket(e["hour_of_day"]) for e in events)
    day_buckets = Counter(DAYS_OF_WEEK[e["day_of_week"]] for e in events)
    cat_buckets = Counter(e["category"] for e in events)

    return {
        "total": total,
        "by_hour_bucket": dict(hour_buckets),
        "by_day_of_week": dict(day_buckets),
        "by_category": dict(cat_buckets),
    }


def check_insight():
    patterns = _compute_patterns()
    if not patterns or patterns["total"] < MIN_EVENTS_FOR_INSIGHT:
        return {"insight": None, "reason": f"need {MIN_EVENTS_FOR_INSIGHT} events, have {patterns['total'] if patterns else 0}"}

    total = patterns["total"]
    threshold = total * PATTERN_DOMINANCE_THRESHOLD

    candidates = []

    # Hour-of-day pattern
    top_hour, hour_count = max(patterns["by_hour_bucket"].items(), key=lambda x: x[1])
    if hour_count >= threshold:
        candidates.append({
            "key": f"hour_{top_hour}",
            "type": "time-of-day",
            "description": f"{int(round(hour_count/total*100))}% of what you ship lands in the {top_hour}",
            "bucket": top_hour,
            "share": round(hour_count / total, 2),
        })

    # Day-of-week pattern
    top_day, day_count = max(patterns["by_day_of_week"].items(), key=lambda x: x[1])
    if day_count >= threshold:
        candidates.append({
            "key": f"day_{top_day}",
            "type": "day-of-week",
            "description": f"{int(round(day_count/total*100))}% of your shipped events have been on {top_day}s",
            "bucket": top_day,
            "share": round(day_count / total, 2),
        })

    if not candidates:
        return {"insight": None, "reason": "no dominant pattern yet"}

    # Filter out anything surfaced this session OR within cooldown
    session = load_session()
    surfaced_session = set(session.get("surfaced_keys", []))

    conn = init_db()
    cur = conn.cursor()
    cooldown_cutoff = (datetime.now() - timedelta(days=INSIGHT_COOLDOWN_DAYS)).isoformat()
    cur.execute(
        "SELECT insight_key FROM surfaced_insights WHERE surfaced_at >= ?",
        (cooldown_cutoff,),
    )
    surfaced_recent = {r["insight_key"] for r in cur.fetchall()}
    conn.close()

    eligible = [
        c for c in candidates
        if c["key"] not in surfaced_session and c["key"] not in surfaced_recent
    ]

    if not eligible:
        return {"insight": None, "reason": "all current patterns already surfaced recently"}

    # Pick the strongest one
    eligible.sort(key=lambda c: c["share"], reverse=True)
    chosen = eligible[0]

    # Mark as surfaced
    conn = init_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO surfaced_insights (insight_key, surfaced_at, description)
        VALUES (?, ?, ?)
        ON CONFLICT(insight_key) DO UPDATE SET
            surfaced_at = excluded.surfaced_at,
            description = excluded.description
        """,
        (chosen["key"], now, chosen["description"]),
    )
    conn.commit()
    conn.close()

    surfaced_session.add(chosen["key"])
    session["surfaced_keys"] = list(surfaced_session)
    save_session(session)

    return {"insight": chosen}


def summary():
    patterns = _compute_patterns()
    if not patterns:
        return {"total": 0, "message": "no events logged yet"}

    total = patterns["total"]

    def top_n(d, n=3):
        return sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]

    return {
        "total_events": total,
        "ready_for_insights": total >= MIN_EVENTS_FOR_INSIGHT,
        "top_time_windows": [
            {"window": k, "count": v, "share": round(v / total, 2)}
            for k, v in top_n(patterns["by_hour_bucket"])
        ],
        "top_days": [
            {"day": k, "count": v, "share": round(v / total, 2)}
            for k, v in top_n(patterns["by_day_of_week"])
        ],
        "by_category": patterns["by_category"],
    }


def list_events(days):
    conn = init_db()
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT * FROM energy_events WHERE timestamp >= ? ORDER BY timestamp DESC",
        (cutoff,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"days": days, "count": len(rows), "events": rows}


def main():
    parser = argparse.ArgumentParser(description="Energy Mapping — track real productive windows")
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log")
    p_log.add_argument("--what", required=True)
    p_log.add_argument("--category", default="general")

    sub.add_parser("check_insight")
    sub.add_parser("summary")

    p_list = sub.add_parser("list")
    p_list.add_argument("--days", type=int, default=30)

    args = parser.parse_args()

    if args.command == "log":
        result = log_event(args.what, args.category)
    elif args.command == "check_insight":
        result = check_insight()
    elif args.command == "summary":
        result = summary()
    elif args.command == "list":
        result = list_events(args.days)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
