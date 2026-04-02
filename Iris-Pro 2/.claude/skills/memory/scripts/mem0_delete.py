#!/usr/bin/env python3
"""
Script: mem0 Delete Memory
Purpose: Delete a specific memory by ID or bulk delete all.

Usage:
    python .claude/skills/memory/scripts/mem0_delete.py --memory-id "abc123"
    python .claude/skills/memory/scripts/mem0_delete.py --all --confirm
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import get_memory_client, USER_ID, HISTORY_DB_PATH


def delete_memory(memory_id):
    m = get_memory_client()
    m.delete(memory_id)
    return {"status": "deleted", "memory_id": memory_id}


def delete_all(confirm=False):
    if not confirm:
        return {"error": "Pass --confirm to delete all memories. This is irreversible."}

    m = get_memory_client()
    try:
        m.delete_all(user_id=USER_ID)
        return {"status": "all_deleted", "user_id": USER_ID}
    except Exception:
        if not HISTORY_DB_PATH.exists():
            return {"error": "No history DB found"}

        conn = sqlite3.connect(str(HISTORY_DB_PATH))
        rows = conn.execute("""
            SELECT DISTINCT memory_id FROM history
            WHERE is_deleted = 0 AND event != 'DELETE'
        """).fetchall()
        conn.close()

        deleted = 0
        for row in rows:
            try:
                m.delete(row[0])
                deleted += 1
            except Exception:
                pass

        return {"status": "all_deleted", "deleted_count": deleted, "method": "individual"}


def main():
    parser = argparse.ArgumentParser(description="Delete mem0 memories")
    parser.add_argument("--memory-id", type=str, help="ID of specific memory to delete")
    parser.add_argument("--all", action="store_true", help="Delete ALL memories")
    parser.add_argument("--confirm", action="store_true", help="Required with --all")
    args = parser.parse_args()

    if args.memory_id:
        result = delete_memory(args.memory_id)
    elif args.all:
        result = delete_all(confirm=args.confirm)
    else:
        result = {"error": "Provide --memory-id or --all"}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
