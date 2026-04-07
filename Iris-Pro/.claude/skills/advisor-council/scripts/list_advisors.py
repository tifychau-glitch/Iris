#!/usr/bin/env python3
"""List all loaded advisors with their metadata.

Usage:
    python3 list_advisors.py
    python3 list_advisors.py --json

Output: Table of advisors with name, domains, source count, last updated.
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ADVISORS_DIR = PROJECT_ROOT / "context" / "advisors"


def get_advisor_info(advisor_dir: Path) -> dict:
    """Extract metadata from an advisor directory."""
    name = advisor_dir.name
    profile_path = advisor_dir / "profile.md"
    sources_dir = advisor_dir / "sources"

    info = {
        "name": name,
        "has_profile": profile_path.exists(),
        "domains": [],
        "source_count": 0,
        "total_words": 0,
        "last_updated": None
    }

    # Count sources
    if sources_dir.exists():
        sources = list(sources_dir.glob("*.md")) + list(sources_dir.glob("*.txt"))
        info["source_count"] = len(sources)
        for src in sources:
            info["total_words"] += len(src.read_text().split())

    # Extract domains from profile
    if profile_path.exists():
        content = profile_path.read_text()
        info["last_updated"] = datetime.fromtimestamp(
            profile_path.stat().st_mtime
        ).strftime("%Y-%m-%d")

        # Look for Expertise Domains section
        for line in content.split('\n'):
            if line.startswith('## Expertise Domains'):
                # Next non-empty line should be the domains
                idx = content.split('\n').index(line)
                remaining = content.split('\n')[idx+1:]
                for next_line in remaining:
                    next_line = next_line.strip()
                    if next_line and not next_line.startswith('#'):
                        info["domains"] = [d.strip() for d in next_line.split(',')]
                        break
                break

        # Get first line summary
        for line in content.split('\n'):
            if line.startswith('>'):
                info["summary"] = line.lstrip('> ').strip()
                break

    return info


def main():
    as_json = "--json" in sys.argv

    if not ADVISORS_DIR.exists():
        if as_json:
            print(json.dumps({"advisors": [], "count": 0}))
        else:
            print("No advisors directory found. Create one with /advisor create.")
        return

    # Find advisor directories (skip README and non-directories)
    advisor_dirs = [d for d in ADVISORS_DIR.iterdir()
                    if d.is_dir() and not d.name.startswith('.')]

    if not advisor_dirs:
        if as_json:
            print(json.dumps({"advisors": [], "count": 0}))
        else:
            print("No advisors loaded yet. Create one with /advisor create.")
        return

    advisors = []
    for d in sorted(advisor_dirs):
        info = get_advisor_info(d)
        advisors.append(info)

    if as_json:
        print(json.dumps({"advisors": advisors, "count": len(advisors)}))
        return

    # Pretty print
    print(f"\n{'='*60}")
    print(f"  LOADED ADVISORS ({len(advisors)})")
    print(f"{'='*60}\n")

    for a in advisors:
        status = "Ready" if a["has_profile"] else "Sources only (needs synthesis)"
        domains = ", ".join(a["domains"][:4]) if a["domains"] else "Not categorized"
        summary = a.get("summary", "")

        print(f"  {a['name'].upper()}")
        if summary:
            print(f"  {summary}")
        print(f"  Domains: {domains}")
        print(f"  Sources: {a['source_count']} ({a['total_words']:,} words)")
        print(f"  Status: {status}")
        if a["last_updated"]:
            print(f"  Last updated: {a['last_updated']}")
        print()

    print(f"{'='*60}")


if __name__ == "__main__":
    main()
