"""
Weekly Pattern Report — Compiles accountability data into a structured report.

Runs every Monday via cron. Pulls weekly_summary, self_trust_score,
promise_vs_proof, streak, and constraint diagnosis. Formats into a
Telegram-deliverable report.

This is the ONE script that uses AI (via claude -p) for interpretation.
All data collection is deterministic Python.

Usage: python3 weekly_report.py [--dry-run] [--chat-id CHAT_ID]
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ENGINE_SCRIPT = SCRIPT_DIR / "accountability_engine.py"
DIAGNOSE_SCRIPT = SCRIPT_DIR.parent.parent / "constraint-finder" / "scripts" / "diagnose.py"
SEND_SCRIPT = (SCRIPT_DIR / "../../../telegram/scripts/telegram_send.py").resolve()


def run_command(script, *args):
    """Run a script and return parsed JSON output."""
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def collect_data():
    """Gather all accountability data for the week."""
    data = {}

    data["weekly_summary"] = run_command(ENGINE_SCRIPT, "weekly_summary")
    data["self_trust"] = run_command(ENGINE_SCRIPT, "self_trust_score")
    data["promise_proof"] = run_command(ENGINE_SCRIPT, "promise_vs_proof")
    data["streak"] = run_command(ENGINE_SCRIPT, "streak")
    data["constraint"] = run_command(DIAGNOSE_SCRIPT, "--min-days", "3")

    return data


def format_report(data):
    """Format the collected data into a readable Telegram message."""
    lines = ["WEEKLY REPORT", ""]

    # Promise vs Proof
    pp = data.get("promise_proof")
    if pp and pp.get("promises_made", 0) > 0:
        rate_pct = int(pp["follow_through_rate"] * 100)
        lines.append(f"Follow-through: {rate_pct}%")
        lines.append(f"Promises: {pp['promises_kept']} kept / {pp['promises_made']} made")
        if pp.get("promises_broken"):
            lines.append(f"Broken: {pp['promises_broken']}")
        if pp.get("promises_unaddressed"):
            lines.append(f"Unaddressed: {pp['promises_unaddressed']}")
        lines.append("")

    # Self-trust
    st = data.get("self_trust")
    if st and st.get("promises_made_14d", 0) > 0:
        trust_pct = int(st["self_trust_score"] * 100)
        trend = st.get("trend", "flat")
        trend_symbol = {"up": "+", "down": "-", "flat": "="}
        lines.append(f"Self-trust score: {trust_pct}% ({trend_symbol.get(trend, '')})")
        lines.append("")

    # Streak
    sk = data.get("streak")
    if sk:
        lines.append(f"Current streak: {sk.get('current_streak', 0)} days")
        lines.append(f"Best streak: {sk.get('best_streak', 0)} days")
        lines.append("")

    # Level
    if pp:
        lines.append(f"Accountability level: {pp.get('level_name', 'Unknown')}")
        lines.append("")

    # Top excuses
    if pp and pp.get("top_excuse_categories"):
        excuses = [f"{e['category']} ({e['count']})" for e in pp["top_excuse_categories"][:3]]
        lines.append(f"Top excuses: {', '.join(excuses)}")
        lines.append("")

    # Constraint diagnosis
    cd = data.get("constraint")
    if cd and cd.get("available") and cd.get("primary_constraint"):
        lines.append(f"Pattern detected: {cd['primary_constraint']}")
        lines.append(cd.get("evidence", ""))
        lines.append("")
        lines.append(f"Next step: {cd.get('suggestion', '')}")
        lines.append("")

    # Weekly breakdown
    ws = data.get("weekly_summary")
    if ws and ws.get("daily_breakdown"):
        lines.append("Daily breakdown:")
        for d in ws["daily_breakdown"]:
            rate_pct = int(d["completion_rate"] * 100)
            bar = "#" * (rate_pct // 10) + "-" * (10 - rate_pct // 10)
            lines.append(f"  {d['date']}: [{bar}] {rate_pct}%")
        lines.append("")

    if len(lines) <= 2:
        return None

    return "\n".join(lines)


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
    parser = argparse.ArgumentParser(description="Weekly Pattern Report")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--chat-id", type=int)
    args = parser.parse_args()

    data = collect_data()
    report = format_report(data)

    if not report:
        print(json.dumps({"status": "no_data", "message": "Not enough data for a weekly report"}))
        sys.exit(0)

    chat_id = args.chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if args.dry_run:
        print("[DRY RUN] Weekly Report:")
        print(report)
    elif chat_id:
        send_telegram(chat_id, report)

    print(json.dumps({
        "status": "sent",
        "has_constraint": bool(data.get("constraint", {}).get("primary_constraint")),
        "dry_run": args.dry_run,
    }))


if __name__ == "__main__":
    main()
