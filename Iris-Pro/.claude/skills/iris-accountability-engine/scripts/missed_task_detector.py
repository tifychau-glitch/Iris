"""
Missed Task Detector — Auto-marks overdue commitments as missed.

Runs daily at 11:55 PM via cron. Finds commitments that passed their due date
without being completed or skipped, and marks them as missed with
excuse_category='unaddressed'.

Usage: python3 missed_task_detector.py [--dry-run]
"""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "iris_accountability.db"
ENGINE_SCRIPT = SCRIPT_DIR / "accountability_engine.py"


def get_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Missed Task Detector")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_connection()
    if not conn:
        sys.exit(0)

    today = datetime.now().strftime("%Y-%m-%d")

    # Find commitments that are overdue and unaddressed
    missed = conn.execute(
        """SELECT id, description, due_date, category FROM commitments
           WHERE due_date <= ? AND completed = 0 AND skipped = 0""",
        (today,)
    ).fetchall()

    if not missed:
        conn.close()
        print(json.dumps({"status": "clean", "missed_count": 0}))
        sys.exit(0)

    marked = []
    for c in missed:
        if args.dry_run:
            print(f"[DRY RUN] Would mark as missed: {c['description']} (due {c['due_date']})")
        else:
            conn.execute(
                """UPDATE commitments SET skipped = 1,
                   skip_reason = 'auto-detected: not completed by due date',
                   excuse_category = 'unaddressed'
                   WHERE id = ?""",
                (c["id"],)
            )
            marked.append({"id": c["id"], "description": c["description"], "due_date": c["due_date"]})

    if not args.dry_run:
        conn.commit()
        # Recalculate today's score
        subprocess.run(
            [sys.executable, str(ENGINE_SCRIPT), "daily_score"],
            capture_output=True, timeout=10
        )

    conn.close()
    print(json.dumps({
        "status": "processed",
        "missed_count": len(missed),
        "marked": marked,
        "dry_run": args.dry_run,
    }, indent=2))


if __name__ == "__main__":
    main()
