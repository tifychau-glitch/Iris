"""
Ghost Detector — Detects user silence and sends escalating nudges.

Runs every 6 hours via cron. Checks the last interaction timestamp.
Escalates through 3 tiers based on silence duration.
Does NOT re-send if already nudged at that tier.

Usage: python3 ghost_detector.py [--dry-run] [--chat-id CHAT_ID]
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
MESSAGES_DB = PROJECT_ROOT / "data" / "messages.db"
SEND_SCRIPT = (SCRIPT_DIR / "../../../telegram/scripts/telegram_send.py").resolve()

# Escalation tiers
TIERS = {
    1: {
        "hours": 24,
        "message": "Hey. Haven't heard from you. Everything good?",
    },
    2: {
        "hours": 48,
        "message": "Two days. What's going on?",
    },
    3: {
        "hours": 72,
        "message": "I notice you tend to disappear when things get hard. That's data, not judgment. What happened?",
    },
}


def get_connection(db_path):
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_last_interaction(conn):
    """Get the most recent interaction timestamp from the interactions table."""
    row = conn.execute(
        "SELECT created_at FROM interactions ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if row:
        return datetime.fromisoformat(row["created_at"])
    return None


def get_last_interaction_from_messages():
    """Fallback: check messages.db for last user message."""
    conn = get_connection(MESSAGES_DB)
    if not conn:
        return None
    row = conn.execute(
        "SELECT timestamp FROM messages WHERE direction = 'in' ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        try:
            return datetime.fromisoformat(row["timestamp"])
        except (ValueError, TypeError):
            return None
    return None


def get_last_commitment(conn):
    """Check when the last commitment was created."""
    row = conn.execute(
        "SELECT created_at FROM commitments ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if row:
        return datetime.fromisoformat(row["created_at"])
    return None


def get_last_nudge_tier(conn):
    """Get the highest tier of ghost_check intervention sent recently."""
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    row = conn.execute(
        """SELECT MAX(tier) as max_tier FROM interventions
           WHERE type = 'ghost_check' AND created_at >= ?""",
        (three_days_ago,)
    ).fetchone()
    return row["max_tier"] if row and row["max_tier"] else 0


def send_telegram(chat_id, message):
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
        print(f"WARN: Failed to send: {e}", file=sys.stderr)
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ghost Detector")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--chat-id", type=int)
    args = parser.parse_args()

    conn = get_connection(DB_PATH)
    if not conn:
        sys.exit(0)

    # Find the most recent interaction from any source
    last = get_last_interaction(conn)
    if not last:
        last = get_last_interaction_from_messages()
    if not last:
        last = get_last_commitment(conn)
    if not last:
        # No data at all — system hasn't been used yet
        conn.close()
        print(json.dumps({"status": "no_data", "message": "No interaction history found"}))
        sys.exit(0)

    hours_silent = (datetime.now() - last).total_seconds() / 3600
    last_tier_sent = get_last_nudge_tier(conn)

    # Determine which tier to send
    target_tier = 0
    for tier_num in sorted(TIERS.keys(), reverse=True):
        if hours_silent >= TIERS[tier_num]["hours"]:
            target_tier = tier_num
            break

    if target_tier == 0 or target_tier <= last_tier_sent:
        # Not enough silence, or already nudged at this tier
        conn.close()
        print(json.dumps({
            "status": "silent",
            "hours_silent": round(hours_silent, 1),
            "last_tier_sent": last_tier_sent,
            "action": "none",
        }))
        sys.exit(0)

    message = TIERS[target_tier]["message"]
    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if args.dry_run:
        print(f"[DRY RUN] Tier {target_tier}: {message}")
    elif chat_id:
        sent = send_telegram(chat_id, message)
        if sent:
            # Log the intervention
            level_row = conn.execute(
                "SELECT accountability_level FROM daily_scores ORDER BY date DESC LIMIT 1"
            ).fetchone()
            level = level_row["accountability_level"] if level_row else 1

            conn.execute(
                """INSERT INTO interventions (type, tier, message_sent, accountability_level)
                   VALUES ('ghost_check', ?, ?, ?)""",
                (target_tier, message, level)
            )
            conn.commit()
    else:
        print(f"[NO CHAT ID] Tier {target_tier}: {message}")

    conn.close()
    print(json.dumps({
        "status": "nudged",
        "hours_silent": round(hours_silent, 1),
        "tier": target_tier,
        "message": message,
        "dry_run": args.dry_run,
    }))


if __name__ == "__main__":
    main()
