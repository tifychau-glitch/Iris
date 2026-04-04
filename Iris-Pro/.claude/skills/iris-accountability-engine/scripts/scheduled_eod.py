"""
Scheduled End-of-Day Capture — Daily close-out ritual.

Runs once daily at configurable evening time. Only fires if the user
had commitments today. Sends a structured results summary via Telegram
and writes to the daily log.

Usage: python3 scheduled_eod.py [--dry-run] [--chat-id CHAT_ID]
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "data" / "iris_accountability.db"
ENGINE_SCRIPT = SCRIPT_DIR / "accountability_engine.py"
SEND_SCRIPT = (SCRIPT_DIR / "../../../telegram/scripts/telegram_send.py").resolve()
LOGS_DIR = PROJECT_ROOT / "memory" / "logs"


def get_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_eod_data():
    """Get end-of-day summary from the accountability engine."""
    result = subprocess.run(
        [sys.executable, str(ENGINE_SCRIPT), "end_of_day"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def format_eod_message(data):
    """Format the EOD data into a human-readable Telegram message."""
    if not data.get("has_data"):
        return None

    lines = [f"End of day — {data['date']}"]
    lines.append("")

    # Completed
    if data["completed"]:
        for c in data["completed"]:
            lines.append(f"  {c['description']}")
    else:
        lines.append("  Nothing completed today.")
    lines.append("")

    # Missed
    if data["missed"]:
        lines.append("Still open:")
        for c in data["missed"]:
            lines.append(f"  {c['description']}")
        lines.append("")

    # Skipped
    if data["skipped"]:
        lines.append("Skipped:")
        for c in data["skipped"]:
            reason = f" — {c['reason']}" if c.get("reason") else ""
            lines.append(f"  {c['description']}{reason}")
        lines.append("")

    # Score
    rate_pct = int(data["completion_rate"] * 100)
    lines.append(f"Completion: {rate_pct}% | Level: {data['level_name']}")
    lines.append("")
    lines.append("What's your one commitment for tomorrow?")

    return "\n".join(lines)


def write_daily_log(data):
    """Append EOD summary to today's daily log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.md"

    entry = [f"\n## End of Day Summary\n"]
    if data["completed"]:
        entry.append("**Completed:**")
        for c in data["completed"]:
            entry.append(f"- {c['description']}")
    if data["missed"]:
        entry.append("\n**Missed:**")
        for c in data["missed"]:
            entry.append(f"- {c['description']}")
    if data["skipped"]:
        entry.append("\n**Skipped:**")
        for c in data["skipped"]:
            entry.append(f"- {c['description']} ({c.get('reason', '')})")

    rate_pct = int(data["completion_rate"] * 100)
    entry.append(f"\n**Completion rate:** {rate_pct}%")
    entry.append(f"**Accountability level:** {data['level_name']}")

    content = "\n".join(entry) + "\n"

    if log_file.exists():
        with open(log_file, "a") as f:
            f.write(content)
    else:
        header = f"# Daily Log: {today}\n\n> Session log for {datetime.now().strftime('%A, %B %d, %Y')}\n\n---\n\n## Events & Notes\n"
        with open(log_file, "w") as f:
            f.write(header + content)


def send_telegram(chat_id, message):
    if not SEND_SCRIPT.exists():
        return False
    try:
        subprocess.run(
            [sys.executable, str(SEND_SCRIPT),
             "--chat-id", str(chat_id), "--message", message],
            capture_output=True, timeout=30
        )
        return True
    except Exception:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scheduled EOD Capture")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--chat-id", type=int)
    args = parser.parse_args()

    data = get_eod_data()
    if not data or not data.get("has_data"):
        print(json.dumps({"status": "skipped", "reason": "no commitments today"}))
        sys.exit(0)

    message = format_eod_message(data)
    if not message:
        sys.exit(0)

    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if args.dry_run:
        print("[DRY RUN] Would send EOD message:")
        print(message)
    elif chat_id:
        send_telegram(chat_id, message)

    # Always write to daily log (even in dry run)
    if not args.dry_run:
        write_daily_log(data)

    print(json.dumps({
        "status": "sent",
        "completion_rate": data["completion_rate"],
        "completed": len(data["completed"]),
        "missed": len(data["missed"]),
        "skipped": len(data["skipped"]),
        "dry_run": args.dry_run,
    }))


if __name__ == "__main__":
    main()
