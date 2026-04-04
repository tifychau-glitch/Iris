"""
Task-to-Commitment Sync — Bridges task-manager and accountability engine.

Queries tasks.db for tasks due today that don't already have a matching
commitment in iris_accountability.db, and creates commitments for them.

Usage: python3 sync_tasks_to_commitments.py [--dry-run]
"""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
TASKS_DB = PROJECT_ROOT / "data" / "tasks.db"
ACCOUNTABILITY_DB = PROJECT_ROOT / "data" / "iris_accountability.db"
ENGINE_SCRIPT = SCRIPT_DIR / "accountability_engine.py"


def get_tasks_due_today():
    """Get pending tasks due today from the task manager."""
    if not TASKS_DB.exists():
        return []
    conn = sqlite3.connect(str(TASKS_DB))
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM tasks WHERE due_date = ? AND status = 'pending'",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_existing_commitments_today():
    """Get today's commitments to avoid duplicates."""
    if not ACCOUNTABILITY_DB.exists():
        return []
    conn = sqlite3.connect(str(ACCOUNTABILITY_DB))
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT description, source FROM commitments WHERE due_date = ?",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_commitment(title, category="general"):
    """Create a commitment via the accountability engine."""
    today = datetime.now().strftime("%Y-%m-%d")
    result = subprocess.run(
        [sys.executable, str(ENGINE_SCRIPT),
         "add_commitment", title,
         "--due", today,
         "--category", category,
         "--source", "task_sync"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Task-to-Commitment Sync")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = get_tasks_due_today()
    if not tasks:
        print(json.dumps({"status": "no_tasks", "synced": 0}))
        sys.exit(0)

    existing = get_existing_commitments_today()
    existing_descriptions = {c["description"] for c in existing}
    # Also check by source to avoid re-syncing
    synced_descriptions = {c["description"] for c in existing if c.get("source") == "task_sync"}

    synced = []
    skipped = []
    for task in tasks:
        title = task["title"]
        if title in existing_descriptions or title in synced_descriptions:
            skipped.append(title)
            continue

        if args.dry_run:
            print(f"[DRY RUN] Would create commitment: {title}")
            synced.append(title)
        else:
            result = create_commitment(title, task.get("project", "general") or "general")
            if result:
                synced.append(title)

    print(json.dumps({
        "status": "synced",
        "tasks_found": len(tasks),
        "commitments_created": len(synced),
        "already_existed": len(skipped),
        "synced": synced,
        "dry_run": args.dry_run,
    }, indent=2))


if __name__ == "__main__":
    main()
