#!/usr/bin/env python3
"""
wiki.py — Layer 2: Curated Wiki

Markdown files in memory/wiki/ with YAML frontmatter. Obsidian-compatible.

This is where reference knowledge, strategy notes, architectural decisions,
and synthesized understanding live. Not canonical facts (that's Core State).
Not raw search chunks (that's the retrieval index).

Wiki pages are the "working understanding" layer — things IRIS has learned
from conversations that aren't hard facts but are worth remembering.

Usage:
    python3 wiki.py --write "Why we chose Pinecone" --content "Each user gets..."
    python3 wiki.py --read "why-we-chose-pinecone"
    python3 wiki.py --list
    python3 wiki.py --search "pinecone"
    python3 wiki.py --stale              # show pages not updated in 90+ days
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_ROOT = _HERE.parents[3]  # Iris-Pro root
WIKI_DIR = _ROOT / "memory" / "wiki"

# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _slugify(title: str) -> str:
    """Convert a title to a filename-safe slug."""
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80].strip("-")


def _make_frontmatter(
    title: str,
    entity_type: str = "synthesis",
    author_type: str = "user_explicit",
    confidence: float = 0.75,
    tags: list = None,
    source_ids: list = None,
    linked_pages: list = None,
) -> str:
    """Generate YAML frontmatter for a wiki page."""
    now = datetime.now(timezone.utc).isoformat()
    page_id = str(uuid.uuid4())[:8]
    return f"""---
id: {page_id}
title: {title}
entity_type: {entity_type}
trust_class: curated
author_type: {author_type}
created_at: {now}
updated_at: {now}
last_reviewed_at: null
confidence: {confidence}
source_ids: {json.dumps(source_ids or [])}
tags: {json.dumps(tags or [])}
status: active
linked_pages: {json.dumps(linked_pages or [])}
---"""


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a wiki page. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Parse JSON arrays
            if val.startswith("["):
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass
            # Parse numbers
            elif val.replace(".", "", 1).isdigit():
                val = float(val) if "." in val else int(val)
            # Parse null
            elif val == "null":
                val = None
            meta[key] = val

    body = parts[2].strip()
    return meta, body


def _update_frontmatter_field(text: str, field: str, value: str) -> str:
    """Update a single field in existing frontmatter."""
    if not text.startswith("---"):
        return text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return text

    lines = parts[1].strip().split("\n")
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            lines[i] = f"{field}: {value}"
            updated = True
            break

    if not updated:
        lines.append(f"{field}: {value}")

    return f"---\n" + "\n".join(lines) + "\n---" + parts[2]


# ---------------------------------------------------------------------------
# Core wiki operations
# ---------------------------------------------------------------------------

def write_page(
    title: str,
    content: str,
    entity_type: str = "synthesis",
    author_type: str = "user_explicit",
    confidence: float = 0.75,
    tags: list = None,
    source_ids: list = None,
    linked_pages: list = None,
) -> dict:
    """
    Create or overwrite a wiki page.

    Returns {"status": "created"|"updated", "path": str, "slug": str}
    """
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(title)
    path = WIKI_DIR / f"{slug}.md"
    existed = path.exists()

    frontmatter = _make_frontmatter(
        title=title,
        entity_type=entity_type,
        author_type=author_type,
        confidence=confidence,
        tags=tags,
        source_ids=source_ids,
        linked_pages=linked_pages,
    )

    full_content = f"{frontmatter}\n\n{content.strip()}\n"
    path.write_text(full_content, encoding="utf-8")

    return {
        "status": "updated" if existed else "created",
        "path": str(path),
        "slug": slug,
        "title": title,
    }


def append_to_page(slug: str, content: str) -> dict:
    """Append content to an existing wiki page. Updates the updated_at timestamp."""
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return {"status": "error", "message": f"Page '{slug}' not found"}

    text = path.read_text(encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    text = _update_frontmatter_field(text, "updated_at", now)
    text = text.rstrip() + f"\n\n{content.strip()}\n"
    path.write_text(text, encoding="utf-8")

    return {"status": "appended", "slug": slug}


def read_page(slug: str) -> dict:
    """Read a wiki page. Returns {metadata, body, path} or error."""
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return {"status": "error", "message": f"Page '{slug}' not found"}

    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    return {"status": "ok", "metadata": meta, "body": body, "path": str(path)}


def list_pages(include_stale: bool = False) -> list[dict]:
    """List all wiki pages with metadata. Returns sorted by updated_at descending."""
    if not WIKI_DIR.exists():
        return []

    pages = []
    for f in WIKI_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        # Skip stale unless requested
        if not include_stale and meta.get("status") == "stale":
            continue
        pages.append({
            "slug": f.stem,
            "title": meta.get("title", f.stem),
            "entity_type": meta.get("entity_type", "unknown"),
            "status": meta.get("status", "active"),
            "updated_at": meta.get("updated_at", ""),
            "confidence": meta.get("confidence", 0),
            "tags": meta.get("tags", []),
            "path": str(f),
        })

    pages.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return pages


def search_pages(query: str, limit: int = 10) -> list[dict]:
    """
    Simple keyword search across wiki pages (title + body).
    Returns matching pages with relevance snippets.
    """
    if not WIKI_DIR.exists():
        return []

    query_lower = query.lower()
    query_terms = query_lower.split()
    results = []

    for f in WIKI_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        text_lower = (meta.get("title", "") + " " + body).lower()

        # All query terms must appear somewhere
        if not all(term in text_lower for term in query_terms):
            continue

        # Find a relevant snippet
        snippet = ""
        for line in body.split("\n"):
            if any(term in line.lower() for term in query_terms):
                snippet = line.strip()[:150]
                break

        results.append({
            "slug": f.stem,
            "title": meta.get("title", f.stem),
            "status": meta.get("status", "active"),
            "confidence": meta.get("confidence", 0),
            "snippet": snippet,
            "path": str(f),
        })

    return results[:limit]


def get_stale_pages(threshold_days: int = 90) -> list[dict]:
    """Return wiki pages that haven't been updated in threshold_days."""
    if not WIKI_DIR.exists():
        return []

    now = datetime.now(timezone.utc)
    stale = []

    for f in WIKI_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        updated_str = meta.get("updated_at", "")
        if not updated_str:
            continue

        try:
            updated = datetime.fromisoformat(str(updated_str))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_days = (now - updated).days
            if age_days > threshold_days:
                stale.append({
                    "slug": f.stem,
                    "title": meta.get("title", f.stem),
                    "age_days": age_days,
                    "updated_at": updated_str,
                    "status": meta.get("status", "active"),
                })
        except (ValueError, TypeError):
            continue

    stale.sort(key=lambda p: p["age_days"], reverse=True)
    return stale


def mark_stale(slug: str) -> dict:
    """Mark a wiki page as stale."""
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return {"status": "error", "message": f"Page '{slug}' not found"}

    text = path.read_text(encoding="utf-8")
    text = _update_frontmatter_field(text, "status", "stale")
    path.write_text(text, encoding="utf-8")
    return {"status": "ok", "slug": slug, "new_status": "stale"}


def archive_page(slug: str) -> dict:
    """Move a wiki page to archived status. Keeps the file but excludes from search."""
    path = WIKI_DIR / f"{slug}.md"
    if not path.exists():
        return {"status": "error", "message": f"Page '{slug}' not found"}

    text = path.read_text(encoding="utf-8")
    text = _update_frontmatter_field(text, "status", "archived")
    path.write_text(text, encoding="utf-8")
    return {"status": "ok", "slug": slug, "new_status": "archived"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IRIS Wiki — Layer 2 curated knowledge")
    parser.add_argument("--write", metavar="TITLE", help="Create/update a wiki page")
    parser.add_argument("--content", help="Page content (used with --write)")
    parser.add_argument("--type", default="synthesis",
                        choices=["concept", "project", "person", "decision", "reference", "synthesis"],
                        help="Entity type")
    parser.add_argument("--append", metavar="SLUG", help="Append content to existing page")
    parser.add_argument("--read", metavar="SLUG", help="Read a wiki page")
    parser.add_argument("--list", action="store_true", help="List all wiki pages")
    parser.add_argument("--search", metavar="QUERY", help="Search wiki pages")
    parser.add_argument("--stale", action="store_true", help="Show stale pages (90+ days)")
    parser.add_argument("--mark-stale", metavar="SLUG", help="Mark a page as stale")
    parser.add_argument("--archive", metavar="SLUG", help="Archive a page")
    args = parser.parse_args()

    if args.write:
        if not args.content:
            print("Error: --content required with --write", file=sys.stderr)
            sys.exit(1)
        result = write_page(args.write, args.content, entity_type=args.type)
        print(f"  {result['status']}: {result['title']}")
        print(f"  path: {result['path']}")

    elif args.append:
        if not args.content:
            print("Error: --content required with --append", file=sys.stderr)
            sys.exit(1)
        result = append_to_page(args.append, args.content)
        print(f"  {result['status']}: {result.get('slug', '')}")

    elif args.read:
        result = read_page(args.read)
        if result["status"] == "error":
            print(f"  Error: {result['message']}", file=sys.stderr)
            sys.exit(1)
        meta = result["metadata"]
        print(f"  Title: {meta.get('title', '?')}")
        print(f"  Type: {meta.get('entity_type', '?')}")
        print(f"  Status: {meta.get('status', '?')}")
        print(f"  Confidence: {meta.get('confidence', '?')}")
        print(f"  Updated: {meta.get('updated_at', '?')}")
        print(f"\n{result['body']}")

    elif args.list:
        pages = list_pages(include_stale=True)
        if not pages:
            print("  No wiki pages found.")
        else:
            print(f"  {len(pages)} wiki page(s):\n")
            for p in pages:
                status = f"[{p['status']}]" if p['status'] != 'active' else ''
                print(f"  {p['slug']:<40} {p['title']:<30} {status}")

    elif args.search:
        results = search_pages(args.search)
        if not results:
            print(f"  No wiki pages match '{args.search}'")
        else:
            print(f"  {len(results)} result(s):\n")
            for r in results:
                print(f"  {r['slug']}: {r['title']}")
                if r['snippet']:
                    print(f"    \"{r['snippet']}\"")

    elif args.stale:
        stale = get_stale_pages()
        if not stale:
            print("  No stale wiki pages.")
        else:
            print(f"  {len(stale)} stale page(s):\n")
            for s in stale:
                print(f"  {s['slug']}: {s['age_days']} days old (updated {s['updated_at'][:10]})")

    elif args.mark_stale:
        result = mark_stale(args.mark_stale)
        print(f"  {result['status']}: {result.get('slug', '')}")

    elif args.archive:
        result = archive_page(args.archive)
        print(f"  {result['status']}: {result.get('slug', '')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
