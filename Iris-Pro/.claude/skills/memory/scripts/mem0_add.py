#!/usr/bin/env python3
"""
Script: mem0 Add Memory
Purpose: Extract and store facts from conversations or explicit content.
         mem0 auto-extracts facts via LLM, deduplicates, and resolves contradictions.

Usage:
    python .claude/skills/memory/scripts/mem0_add.py --content "User prefers Claude for coding tasks"
    python .claude/skills/memory/scripts/mem0_add.py --messages '[{"role":"user","content":"I switched to ClickUp"}]'
    python .claude/skills/memory/scripts/mem0_add.py --content "API limit is 100/hour" --metadata '{"category":"technical"}'
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import get_memory_client, USER_ID, sanitize_text


def add_memory(content=None, messages=None, metadata=None):
    m = get_memory_client()
    kwargs = {"user_id": USER_ID}
    if metadata:
        kwargs["metadata"] = metadata
    # Scrub secrets before sending to OpenAI/Pinecone
    if messages:
        messages = [{"role": msg["role"], "content": sanitize_text(msg["content"])} for msg in messages]
        result = m.add(messages, **kwargs)
    elif content:
        content = sanitize_text(content)
        result = m.add(content, **kwargs)
    else:
        return {"error": "Provide --content or --messages"}

    # Index new/updated memories in FTS5 for hybrid search
    try:
        from smart_search import index_single_memory
        events = result.get("results", []) if isinstance(result, dict) else []
        for event in events:
            mid = event.get("id", "")
            mem_text = event.get("memory", "")
            if mid and mem_text:
                index_single_memory(mid, mem_text)
    except Exception:
        pass  # FTS indexing is best-effort

    return result


def main():
    parser = argparse.ArgumentParser(description="Add memories via mem0 fact extraction")
    parser.add_argument("--content", type=str, help="Plain text content to remember")
    parser.add_argument("--messages", type=str, help="JSON array of {role, content} message dicts")
    parser.add_argument("--metadata", type=str, help="JSON dict of metadata tags")
    args = parser.parse_args()

    messages = json.loads(args.messages) if args.messages else None
    metadata = json.loads(args.metadata) if args.metadata else None

    result = add_memory(content=args.content, messages=messages, metadata=metadata)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
