"""
Tool: Iris Accountability Engine
Purpose: Core engine for tracking commitments, calculating accountability levels,
         and providing Iris with personality/tone context based on user behavior.
Usage: python3 scripts/accountability_engine.py <command> [options]

Commands:
  add_commitment    Log a new commitment
  complete          Mark a commitment as done
  skip              Mark a commitment as skipped (with reason)
  daily_score       Calculate today's score and accountability level
  get_level         Get current accountability level with personality context
  calibrate         Set user preferences (max level, swearing, schedule)
  get_calibration   Return current calibration settings
  weekly_summary    7-day stats, streaks, and patterns
  streak            Current streak info for active goals
  list_commitments  Show commitments (today, pending, or all)
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "iris_accountability.db"

# Iris personality at each level
LEVEL_PROFILES = {
    1: {
        "name": "Sweet Iris",
        "description": "Genuinely encouraging and proud",
        "tone": "warm, supportive, celebrating wins",
        "examples": [
            "Look at you go! I knew you had it in you.",
            "Ok I see you! Three days in a row? That's not luck, that's discipline.",
            "You actually did all three things today. I'm honestly impressed.",
        ],
    },
    2: {
        "name": "Subtle Side-Eye",
        "description": "Passive guilt trip, says it's fine but it's clearly not",
        "tone": "warm on the surface, subtle disappointment underneath",
        "examples": [
            "Oh you didn't do it? No worries. I'm sure tomorrow will be different.",
            "That's fine. Rest is important too... I guess.",
            "No judgment. Well, maybe a little. But mostly no judgment.",
        ],
    },
    3: {
        "name": "Passive Aggressive Check-In",
        "description": "Pattern is forming, Iris is noticing and calling it out indirectly",
        "tone": "pointed questions, rhetorical observations, concerned but sarcastic",
        "examples": [
            "So I noticed you said you'd do this three days ago. Just wondering if we're still doing goals or if we've moved on to something else?",
            "Hey quick question. When you said you'd do it 'tomorrow,' which tomorrow did you mean exactly?",
            "I'm not saying there's a pattern here, but if I were saying that, the pattern would be pretty obvious.",
        ],
    },
    4: {
        "name": "Direct Confrontation",
        "description": "Dropping the act, real talk, still caring but not sugarcoating",
        "tone": "direct, honest, no-BS, cuts through excuses",
        "examples": [
            "Hey. Real talk. You told me this mattered to you. Was that true or were we just having a moment?",
            "I need you to be honest with me right now. What's actually going on? Because the excuses aren't adding up.",
            "Look, I can keep sending you check-ins that you ignore, or we can figure out what's actually blocking you. Your call.",
        ],
    },
    5: {
        "name": "Full Drill Sergeant",
        "description": "No more playing nice, full intensity accountability",
        "tone": "commanding, urgent, zero tolerance for excuses, tough love",
        "examples": [
            "Get up. Open the laptop. I don't want to hear it. You can feel sorry for yourself AFTER you do the work.",
            "You know what's standing between you and your goals? It's not time. It's not resources. It's you choosing comfort over progress. Every. Single. Day.",
            "I'm done being nice about this. You said this mattered. Prove it. Right now. Not tomorrow. NOW.",
        ],
    },
}


def get_connection():
    """Get or create database connection with table setup."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            recurring INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            due_date TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            skipped INTEGER DEFAULT 0,
            skip_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            commitments_made INTEGER DEFAULT 0,
            commitments_completed INTEGER DEFAULT 0,
            completion_rate REAL DEFAULT 0.0,
            accountability_level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_calibration (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_level INTEGER DEFAULT 5,
            swearing_ok INTEGER DEFAULT 0,
            wake_time TEXT DEFAULT '07:00',
            sleep_time TEXT DEFAULT '23:00',
            check_in_times TEXT DEFAULT '["08:00", "13:00", "20:00"]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO user_calibration (id) VALUES (1);
    """)
    conn.commit()
    return conn


def add_commitment(args):
    """Log a new commitment."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO commitments (description, category, due_date, recurring)
           VALUES (?, ?, ?, ?)""",
        (args.description, args.category or "general",
         args.due or datetime.now().strftime("%Y-%m-%d"),
         1 if args.recurring else 0)
    )
    conn.commit()
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    print(json.dumps({
        "status": "added",
        "id": cid,
        "description": args.description,
        "due_date": args.due or datetime.now().strftime("%Y-%m-%d"),
        "recurring": bool(args.recurring),
    }))


def complete_commitment(args):
    """Mark a commitment as completed."""
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE commitments SET completed = 1, completed_at = ? WHERE id = ?",
        (now, args.id)
    )
    conn.commit()
    row = conn.execute("SELECT description FROM commitments WHERE id = ?", (args.id,)).fetchone()
    conn.close()
    desc = row["description"] if row else "(unknown)"
    print(json.dumps({"status": "completed", "id": args.id, "description": desc}))


def skip_commitment(args):
    """Mark a commitment as skipped with a reason."""
    conn = get_connection()
    conn.execute(
        "UPDATE commitments SET skipped = 1, skip_reason = ? WHERE id = ?",
        (args.reason or "no reason given", args.id)
    )
    conn.commit()
    row = conn.execute("SELECT description FROM commitments WHERE id = ?", (args.id,)).fetchone()
    conn.close()
    desc = row["description"] if row else "(unknown)"
    print(json.dumps({
        "status": "skipped",
        "id": args.id,
        "description": desc,
        "reason": args.reason or "no reason given",
    }))


def calculate_level(completion_rates, max_level):
    """Calculate accountability level from recent completion rates."""
    if not completion_rates:
        return 1

    avg_rate = sum(completion_rates) / len(completion_rates)

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

    return min(level, max_level)


def daily_score(args):
    """Calculate today's score and accountability level."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")

    # Count today's commitments
    made = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date = ? AND skipped = 0",
        (today,)
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date = ? AND completed = 1",
        (today,)
    ).fetchone()[0]

    rate = (completed / made) if made > 0 else 0.0

    # Get last 7 days of scores for level calculation
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    past_scores = conn.execute(
        "SELECT completion_rate FROM daily_scores WHERE date >= ? AND date < ?",
        (week_ago, today)
    ).fetchall()

    rates = [r["completion_rate"] for r in past_scores] + [rate]

    # Get calibration
    cal = conn.execute("SELECT max_level FROM user_calibration WHERE id = 1").fetchone()
    max_level = cal["max_level"] if cal else 5

    level = calculate_level(rates, max_level)

    # Upsert today's score
    conn.execute(
        """INSERT INTO daily_scores (date, commitments_made, commitments_completed, completion_rate, accountability_level)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
             commitments_made = excluded.commitments_made,
             commitments_completed = excluded.commitments_completed,
             completion_rate = excluded.completion_rate,
             accountability_level = excluded.accountability_level""",
        (today, made, completed, round(rate, 2), level)
    )
    conn.commit()
    conn.close()

    profile = LEVEL_PROFILES[level]
    print(json.dumps({
        "date": today,
        "commitments_made": made,
        "commitments_completed": completed,
        "completion_rate": round(rate, 2),
        "accountability_level": level,
        "level_name": profile["name"],
        "level_tone": profile["tone"],
    }, indent=2))


def get_level(args):
    """Return current accountability level with full personality context."""
    conn = get_connection()

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    past_scores = conn.execute(
        "SELECT completion_rate FROM daily_scores WHERE date >= ?",
        (week_ago,)
    ).fetchall()

    rates = [r["completion_rate"] for r in past_scores]

    cal = conn.execute("SELECT * FROM user_calibration WHERE id = 1").fetchone()
    max_level = cal["max_level"] if cal else 5
    swearing_ok = bool(cal["swearing_ok"]) if cal else False

    level = calculate_level(rates, max_level)
    profile = LEVEL_PROFILES[level]

    conn.close()
    print(json.dumps({
        "accountability_level": level,
        "level_name": profile["name"],
        "description": profile["description"],
        "tone": profile["tone"],
        "example_responses": profile["examples"],
        "swearing_ok": swearing_ok,
        "max_level": max_level,
        "based_on_days": len(rates),
        "avg_completion_rate": round(sum(rates) / len(rates), 2) if rates else None,
    }, indent=2))


def calibrate(args):
    """Set user preferences."""
    conn = get_connection()
    now = datetime.now().isoformat()

    updates = []
    params = []

    if args.max_level is not None:
        updates.append("max_level = ?")
        params.append(max(1, min(5, args.max_level)))
    if args.swearing is not None:
        updates.append("swearing_ok = ?")
        params.append(1 if args.swearing.lower() in ("ok", "yes", "true", "1") else 0)
    if args.wake:
        updates.append("wake_time = ?")
        params.append(args.wake)
    if args.sleep:
        updates.append("sleep_time = ?")
        params.append(args.sleep)
    if args.check_ins:
        updates.append("check_in_times = ?")
        params.append(json.dumps(args.check_ins.split(",")))

    if updates:
        updates.append("updated_at = ?")
        params.append(now)
        query = f"UPDATE user_calibration SET {', '.join(updates)} WHERE id = 1"
        conn.execute(query, params)
        conn.commit()

    # Return current calibration
    cal = conn.execute("SELECT * FROM user_calibration WHERE id = 1").fetchone()
    conn.close()

    print(json.dumps({
        "status": "calibrated",
        "max_level": cal["max_level"],
        "swearing_ok": bool(cal["swearing_ok"]),
        "wake_time": cal["wake_time"],
        "sleep_time": cal["sleep_time"],
        "check_in_times": json.loads(cal["check_in_times"]),
    }, indent=2))


def get_calibration(args):
    """Return current calibration settings."""
    conn = get_connection()
    cal = conn.execute("SELECT * FROM user_calibration WHERE id = 1").fetchone()
    conn.close()

    print(json.dumps({
        "max_level": cal["max_level"],
        "max_level_name": LEVEL_PROFILES[cal["max_level"]]["name"],
        "swearing_ok": bool(cal["swearing_ok"]),
        "wake_time": cal["wake_time"],
        "sleep_time": cal["sleep_time"],
        "check_in_times": json.loads(cal["check_in_times"]),
    }, indent=2))


def weekly_summary(args):
    """Return 7-day stats with patterns."""
    conn = get_connection()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    scores = conn.execute(
        "SELECT * FROM daily_scores WHERE date >= ? ORDER BY date",
        (week_ago,)
    ).fetchall()

    if not scores:
        conn.close()
        print(json.dumps({"message": "No data for the past 7 days", "days_tracked": 0}))
        return

    days = [dict(s) for s in scores]
    rates = [d["completion_rate"] for d in days]
    total_made = sum(d["commitments_made"] for d in days)
    total_completed = sum(d["commitments_completed"] for d in days)

    # Find best and worst days
    best_day = max(days, key=lambda d: d["completion_rate"])
    worst_day = min(days, key=lambda d: d["completion_rate"])

    # Current streak (consecutive days with >= 80% completion)
    streak = 0
    for d in reversed(days):
        if d["completion_rate"] >= 0.80:
            streak += 1
        else:
            break

    conn.close()
    print(json.dumps({
        "period": f"{week_ago} to {datetime.now().strftime('%Y-%m-%d')}",
        "days_tracked": len(days),
        "total_commitments": total_made,
        "total_completed": total_completed,
        "overall_completion_rate": round(total_completed / total_made, 2) if total_made > 0 else 0,
        "avg_daily_rate": round(sum(rates) / len(rates), 2),
        "best_day": {"date": best_day["date"], "rate": best_day["completion_rate"]},
        "worst_day": {"date": worst_day["date"], "rate": worst_day["completion_rate"]},
        "current_streak": streak,
        "daily_breakdown": days,
    }, indent=2))


def streak_info(args):
    """Return current streak information."""
    conn = get_connection()

    scores = conn.execute(
        "SELECT * FROM daily_scores ORDER BY date DESC LIMIT 30"
    ).fetchall()

    if not scores:
        conn.close()
        print(json.dumps({"current_streak": 0, "best_streak": 0, "message": "No data yet"}))
        return

    # Current streak (consecutive days >= 80%)
    current_streak = 0
    for s in scores:
        if s["completion_rate"] >= 0.80:
            current_streak += 1
        else:
            break

    # Best streak ever
    all_scores = conn.execute(
        "SELECT completion_rate FROM daily_scores ORDER BY date"
    ).fetchall()

    best_streak = 0
    running = 0
    for s in all_scores:
        if s["completion_rate"] >= 0.80:
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 0

    # Total days tracked
    total_days = len(all_scores)
    good_days = sum(1 for s in all_scores if s["completion_rate"] >= 0.80)

    conn.close()
    print(json.dumps({
        "current_streak": current_streak,
        "best_streak": best_streak,
        "total_days_tracked": total_days,
        "good_days": good_days,
        "good_day_percentage": round(good_days / total_days, 2) if total_days > 0 else 0,
    }, indent=2))


def list_commitments(args):
    """List commitments with optional filters."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")

    if args.filter == "today":
        rows = conn.execute(
            "SELECT * FROM commitments WHERE due_date = ? ORDER BY completed, id",
            (today,)
        ).fetchall()
    elif args.filter == "pending":
        rows = conn.execute(
            "SELECT * FROM commitments WHERE completed = 0 AND skipped = 0 ORDER BY due_date, id"
        ).fetchall()
    elif args.filter == "overdue":
        rows = conn.execute(
            "SELECT * FROM commitments WHERE completed = 0 AND skipped = 0 AND due_date < ? ORDER BY due_date",
            (today,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM commitments ORDER BY due_date DESC, id LIMIT 50"
        ).fetchall()

    conn.close()
    commitments = [dict(r) for r in rows]
    print(json.dumps({"commitments": commitments, "count": len(commitments)}, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Iris Accountability Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add_commitment
    add_p = subparsers.add_parser("add_commitment")
    add_p.add_argument("description")
    add_p.add_argument("--due")
    add_p.add_argument("--category", default="general")
    add_p.add_argument("--recurring", action="store_true")

    # complete
    comp_p = subparsers.add_parser("complete")
    comp_p.add_argument("id", type=int)

    # skip
    skip_p = subparsers.add_parser("skip")
    skip_p.add_argument("id", type=int)
    skip_p.add_argument("--reason", default="")

    # daily_score
    subparsers.add_parser("daily_score")

    # get_level
    subparsers.add_parser("get_level")

    # calibrate
    cal_p = subparsers.add_parser("calibrate")
    cal_p.add_argument("--max-level", type=int, dest="max_level")
    cal_p.add_argument("--swearing")
    cal_p.add_argument("--wake")
    cal_p.add_argument("--sleep")
    cal_p.add_argument("--check-ins", dest="check_ins")

    # get_calibration
    subparsers.add_parser("get_calibration")

    # weekly_summary
    subparsers.add_parser("weekly_summary")

    # streak
    subparsers.add_parser("streak")

    # list_commitments
    list_p = subparsers.add_parser("list_commitments")
    list_p.add_argument("--filter", choices=["today", "pending", "overdue", "all"], default="today")

    args = parser.parse_args()

    commands = {
        "add_commitment": add_commitment,
        "complete": complete_commitment,
        "skip": skip_commitment,
        "daily_score": daily_score,
        "get_level": get_level,
        "calibrate": calibrate,
        "get_calibration": get_calibration,
        "weekly_summary": weekly_summary,
        "streak": streak_info,
        "list_commitments": list_commitments,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
