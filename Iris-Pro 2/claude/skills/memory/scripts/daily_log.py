#!/usr/bin/env python3
"""
Script: Daily Log Writer
Purpose: Append entries to today's daily session log.
         Daily logs are NOT managed by mem0 — they are a session-continuity mechanism.

Usage:
    python .claude/skills/memory/scripts/daily_log.py --content "Started mem0 integration" --type event
    python .claude/skills/memory/scripts/daily_log.py --content "Quick note"
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import PROJECT_ROOT

LOGS_DIR = PROJECT_ROOT / "memory" / "logs"


def get_today_log_path():
    return LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"


def ensure_log_file(log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        today = datetime.now()
        header = (
            f"# Daily Log: {today.strftime('%Y-%m-%d')}\n\n"
            f"> Session log for {today.strftime('%A, %B %d, %Y')}\n\n"
            f"---\n\n"
            f"## Events & Notes\n\n"
        )
        log_path.write_text(header)


def append_to_log(content, entry_type="note"):
    log_path = get_today_log_path()
    ensure_log_file(log_path)

    timestamp = datetime.now().strftime("%H:%M")
    prefix = f"[{entry_type}]" if entry_type != "note" else ""
    line = f"- {timestamp} {prefix} {content}\n" if prefix else f"- {timestamp} {content}\n"

    with open(log_path, "a") as f:
        f.write(line)

    return {"status": "logged", "path": str(log_path), "entry": line.strip()}


def main():
    parser = argparse.ArgumentParser(description="Append to daily session log")
    parser.add_argument("--content", type=str, required=True, help="Log entry content")
    parser.add_argument("--type", type=str, default="note",
                        choices=["note", "event", "decision", "error", "insight"],
                        help="Entry type (default: note)")
    args = parser.parse_args()

    result = append_to_log(args.content, args.type)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
