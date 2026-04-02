#!/usr/bin/env python3
"""
Script: mem0 Sync to MEMORY.md
Purpose: Read all mem0 memories, classify into sections, regenerate memory/MEMORY.md.
         This is a manual utility — run it when you want a human-readable snapshot.

Usage:
    python .claude/skills/memory/scripts/mem0_sync_md.py --dry-run
    python .claude/skills/memory/scripts/mem0_sync_md.py
"""

import argparse
import json
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from mem0_client import get_memory_client, USER_ID, PROJECT_ROOT, HISTORY_DB_PATH

load_dotenv(PROJECT_ROOT / ".env")

MEMORY_MD_PATH = PROJECT_ROOT / "memory" / "MEMORY.md"

SECTIONS = [
    "User Preferences",
    "Key Facts",
    "Learned Behaviors",
    "Current Projects",
    "Relationships",
    "Technical Context",
]


def _list_from_history(limit=200):
    """Fallback: reconstruct current memory state from the SQLite history DB."""
    if not HISTORY_DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(HISTORY_DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT h.memory_id, h.new_memory as memory, h.event, h.created_at
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

    return [{"id": row["memory_id"], "memory": row["memory"]} for row in rows]


def classify_memories(memories):
    """Use LLM to classify each memory into a MEMORY.md section."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    memory_texts = []
    for mem in memories:
        text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
        if text:
            memory_texts.append(text)

    if not memory_texts:
        return {section: [] for section in SECTIONS}

    classified = {section: [] for section in SECTIONS}
    chunk_size = 30

    for i in range(0, len(memory_texts), chunk_size):
        chunk = memory_texts[i:i + chunk_size]
        numbered = "\n".join(f"{j+1}. {text}" for j, text in enumerate(chunk))

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[{
                "role": "system",
                "content": f"""Classify each numbered memory into exactly one section.
Sections: {json.dumps(SECTIONS)}

Return JSON: {{"classifications": [{{"index": 1, "section": "User Preferences"}}, ...]}}

Rules:
- Preferences/settings/style -> "User Preferences"
- Business info/company/goals -> "Key Facts"
- Patterns/mistakes/debugging tips -> "Learned Behaviors"
- Active work/ongoing tasks -> "Current Projects"
- People/companies/connections -> "Relationships"
- Tech stack/APIs/tools/architecture -> "Technical Context"
"""
            }, {
                "role": "user",
                "content": numbered
            }]
        )

        try:
            result = json.loads(response.choices[0].message.content)
            for item in result.get("classifications", []):
                idx = item.get("index", 0) - 1
                section = item.get("section", "Key Facts")
                if 0 <= idx < len(chunk) and section in SECTIONS:
                    classified[section].append(chunk[idx])
        except (json.JSONDecodeError, KeyError):
            for text in chunk:
                classified["Key Facts"].append(text)

    return classified


def render_memory_md(classified):
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# Persistent Memory",
        "",
        "> This file is auto-synced from mem0. Edit via `mem0_add.py` or directly here.",
        "> Run `mem0_sync_md.py` to regenerate from the full memory store.",
        "",
    ]

    for section in SECTIONS:
        items = classified.get(section, [])
        lines.append(f"## {section}")
        lines.append("")
        if items:
            for item in items:
                clean = item.strip().replace("\n", " ")
                if not clean.startswith("- "):
                    clean = f"- {clean}"
                lines.append(clean)
        else:
            lines.append("- (none)")
        lines.append("")

    lines.append("---")
    lines.append(f"*Last synced: {today}*")
    lines.append("*Source of truth: mem0 vector store. This file is the curated human-readable layer.*")
    lines.append("")

    return "\n".join(lines)


def sync(dry_run=False):
    m = get_memory_client()

    try:
        all_memories = m.get_all(user_id=USER_ID)
        if isinstance(all_memories, dict) and "results" in all_memories:
            memories = all_memories["results"]
        elif isinstance(all_memories, list):
            memories = all_memories
        else:
            memories = []
    except Exception:
        memories = _list_from_history()

    print(f"Found {len(memories)} memories in mem0")

    if not memories:
        print("No memories to sync. MEMORY.md will have empty sections.")

    classified = classify_memories(memories)
    for section, items in classified.items():
        print(f"  {section}: {len(items)} items")

    new_content = render_memory_md(classified)

    if dry_run:
        print("\n--- DRY RUN: Would write to MEMORY.md ---")
        print(new_content)
        return {"status": "dry_run", "total_memories": len(memories)}

    MEMORY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_MD_PATH.write_text(new_content)
    print(f"\nWritten to {MEMORY_MD_PATH}")

    return {"status": "synced", "total_memories": len(memories), "path": str(MEMORY_MD_PATH)}


def main():
    parser = argparse.ArgumentParser(description="Sync mem0 memories to MEMORY.md")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    result = sync(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
