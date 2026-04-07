"""
Followup Engine — Event-driven commitment follow-ups.

Runs periodically (every 30 min via cron). Checks for commitments that need
follow-up based on their due time/date. Sends Telegram messages when relevant.
Exits silently when nothing needs attention.

Usage: python3 followup_engine.py [--dry-run] [--chat-id CHAT_ID]
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "data" / "iris_accountability.db"
SEND_SCRIPT = (SCRIPT_DIR / "../../../telegram/scripts/telegram_send.py").resolve()


def get_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_calibration(conn):
    row = conn.execute("SELECT * FROM user_calibration WHERE id = 1").fetchone()
    if not row:
        return {"wake_time": "07:00", "sleep_time": "23:00"}
    return dict(row)


def is_waking_hours(cal):
    """Check if current time is within user's waking hours."""
    now = datetime.now().strftime("%H:%M")
    wake = cal.get("wake_time", "07:00")
    sleep = cal.get("sleep_time", "23:00")
    return wake <= now <= sleep


def send_telegram(chat_id, message):
    """Send a message via telegram_send.py."""
    if not SEND_SCRIPT.exists():
        print(f"WARN: telegram_send.py not found at {SEND_SCRIPT}", file=sys.stderr)
        return False
    try:
        subprocess.run(
            [sys.executable, str(SEND_SCRIPT),
             "--chat-id", str(chat_id), "--message", message],
            capture_output=True, timeout=30
        )
        return True
    except Exception as e:
        print(f"WARN: Failed to send Telegram: {e}", file=sys.stderr)
        return False


def log_intervention(conn, intervention_type, message, commitment_id=None, tier=1):
    """Log an intervention to the interventions table."""
    level_row = conn.execute(
        "SELECT accountability_level FROM daily_scores ORDER BY date DESC LIMIT 1"
    ).fetchone()
    level = level_row["accountability_level"] if level_row else 1

    conn.execute(
        """INSERT INTO interventions (type, tier, message_sent, commitment_id, accountability_level)
           VALUES (?, ?, ?, ?, ?)""",
        (intervention_type, tier, message[:500], commitment_id, level)
    )
    conn.commit()


def check_overdue_commitments(conn):
    """Find commitments past their due date/time that haven't been followed up."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    results = []

    # Commitments with a specific due_time that have passed
    timed = conn.execute(
        """SELECT * FROM commitments
           WHERE due_date = ? AND due_time IS NOT NULL AND due_time <= ?
           AND completed = 0 AND skipped = 0
           AND (last_followup_sent IS NULL OR last_followup_sent < ?)""",
        (today, current_time, today)
    ).fetchall()

    for c in timed:
        results.append({
            "id": c["id"],
            "description": c["description"],
            "type": "overdue_timed",
            "message": f"Did you finish: {c['description']}? It was due at {c['due_time']}."
        })

    # Commitments from previous days that are still open (no due_time)
    old = conn.execute(
        """SELECT * FROM commitments
           WHERE due_date < ? AND completed = 0 AND skipped = 0
           AND (last_followup_sent IS NULL OR last_followup_sent < ?)""",
        (today, today)
    ).fetchall()

    for c in old:
        days_overdue = (now - datetime.strptime(c["due_date"], "%Y-%m-%d")).days
        results.append({
            "id": c["id"],
            "description": c["description"],
            "type": "overdue_old",
            "message": f"This has been sitting for {days_overdue} day{'s' if days_overdue != 1 else ''}: {c['description']}. Still on it?"
        })

    return results


def check_approaching_deadlines(conn):
    """Find commitments due within the next hour."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    one_hour = (now + timedelta(hours=1)).strftime("%H:%M")

    results = []

    approaching = conn.execute(
        """SELECT * FROM commitments
           WHERE due_date = ? AND due_time IS NOT NULL
           AND due_time > ? AND due_time <= ?
           AND completed = 0 AND skipped = 0
           AND last_followup_sent IS NULL""",
        (today, current_time, one_hour)
    ).fetchall()

    for c in approaching:
        results.append({
            "id": c["id"],
            "description": c["description"],
            "type": "approaching",
            "message": f"Heads up — {c['description']} is due at {c['due_time']}."
        })

    return results


def check_stale_commitments(conn):
    """Find commitments made today with no update in 4+ hours."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    four_hours_ago = (now - timedelta(hours=4)).isoformat()

    results = []

    stale = conn.execute(
        """SELECT * FROM commitments
           WHERE due_date = ? AND due_time IS NULL
           AND completed = 0 AND skipped = 0
           AND created_at <= ?
           AND last_followup_sent IS NULL""",
        (today, four_hours_ago)
    ).fetchall()

    for c in stale:
        results.append({
            "id": c["id"],
            "description": c["description"],
            "type": "stale",
            "message": f"How's this going: {c['description']}?"
        })

    return results


def mark_followed_up(conn, commitment_ids):
    """Mark commitments as followed up today."""
    today = datetime.now().strftime("%Y-%m-%d")
    for cid in commitment_ids:
        conn.execute(
            "UPDATE commitments SET last_followup_sent = ? WHERE id = ?",
            (today, cid)
        )
    conn.commit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Followup Engine")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without sending")
    parser.add_argument("--chat-id", type=int, help="Telegram chat ID (or from env TELEGRAM_CHAT_ID)")
    args = parser.parse_args()

    conn = get_connection()
    if not conn:
        sys.exit(0)  # No DB yet, nothing to do

    cal = get_calibration(conn)
    if not is_waking_hours(cal):
        conn.close()
        sys.exit(0)  # Outside waking hours, exit silently

    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID")

    # Collect all follow-ups needed
    actions = []
    actions.extend(check_overdue_commitments(conn))
    actions.extend(check_approaching_deadlines(conn))
    actions.extend(check_stale_commitments(conn))

    if not actions:
        conn.close()
        sys.exit(0)  # Nothing to follow up on

    # Send messages
    sent_ids = []
    for action in actions:
        if args.dry_run:
            print(f"[DRY RUN] Would send: {action['message']}")
        elif chat_id:
            sent = send_telegram(chat_id, action["message"])
            if sent:
                log_intervention(conn, "followup", action["message"],
                                 commitment_id=action["id"])
                sent_ids.append(action["id"])
        else:
            print(f"[NO CHAT ID] {action['message']}")

    if sent_ids:
        mark_followed_up(conn, sent_ids)

    conn.close()

    # Output summary
    print(json.dumps({
        "actions_found": len(actions),
        "messages_sent": len(sent_ids),
        "dry_run": args.dry_run,
    }))


if __name__ == "__main__":
    main()
