#!/usr/bin/env python3
"""
Script: mem0 List Memories
Purpose: List all memories. Falls back to history DB if Pinecone get_all() fails.

Usage:
    python .claude/skills/memory/scripts/mem0_list.py
    python .claude/skills/memory/scripts/mem0_list.py --limit 20
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import get_memory_client, USER_ID, HISTORY_DB_PATH


def list_memories(limit=100):
    m = get_memory_client()
    try:
        results = m.get_all(user_id=USER_ID)
        if isinstance(results, dict) and "results" in results:
            results["results"] = results["results"][:limit]
        elif isinstance(results, list):
            results = results[:limit]
        return results
    except Exception:
        return _list_from_history(limit)


def _list_from_history(limit=100):
    """Reconstruct current memory state from the history DB audit trail."""
    if not HISTORY_DB_PATH.exists():
        return {"results": [], "source": "history_db", "note": "No history DB found"}

    conn = sqlite3.connect(str(HISTORY_DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT h.memory_id, h.new_memory as memory, h.event, h.created_at, h.updated_at
        FROM history h
        INNER JOIN (
            SELECT memory_id, MAX(rowid) as max_rowid
            FROM history
            WHERE is_deleted = 0
            GROUP BY memory_id
        ) latest ON h.memory_id = latest.memory_id AND h.rowid = latest.max_rowid
        WHERE h.event != 'DELETE'
        ORDER BY h.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

    conn.close()

    memories = []
    for row in rows:
        memories.append({
            "id": row["memory_id"],
            "memory": row["memory"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return {"results": memories, "source": "history_db"}


def main():
    parser = argparse.ArgumentParser(description="List all mem0 memories")
    parser.add_argument("--limit", type=int, default=100, help="Max memories to return")
    args = parser.parse_args()

    results = list_memories(args.limit)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
