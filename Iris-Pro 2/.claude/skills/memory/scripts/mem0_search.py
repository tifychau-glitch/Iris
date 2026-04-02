#!/usr/bin/env python3
"""
Script: mem0 Search Memory
Purpose: Semantic search across all stored memories.

Usage:
    python .claude/skills/memory/scripts/mem0_search.py --query "image generation preferences"
    python .claude/skills/memory/scripts/mem0_search.py --query "API rate limits" --limit 5
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import get_memory_client, USER_ID


def search_memory(query, limit=10):
    m = get_memory_client()
    results = m.search(query, user_id=USER_ID, limit=limit)
    return results


def main():
    parser = argparse.ArgumentParser(description="Search memories via mem0")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    args = parser.parse_args()

    results = search_memory(args.query, args.limit)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
