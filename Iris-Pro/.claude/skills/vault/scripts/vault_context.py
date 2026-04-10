#!/usr/bin/env python3
"""
Vault Context — loads the user's identity and recent context at session start.

This script is called by IRIS at the start of every conversation with a
returning user whose vault is connected. It reads:

- index.md (vault navigation)
- me.md (identity)
- my-everest.md (north star)
- my-business.md (current focus)
- my-voice.md (how they communicate)
- maps/iris-rules.md (user's behavioral rules for IRIS)
- Calendar/<most-recent>.md (yesterday's context, for continuity)

Gracefully handles:
- No vault configured (IRIS_VAULT_PATH unset) — returns empty with status
- Vault path doesn't exist — returns empty with status
- Individual files missing — skipped silently, others still load
- Files that are just guidance comments — loaded as-is

Usage:
    python3 vault_context.py                # formatted markdown to stdout
    python3 vault_context.py --format json  # structured JSON
    python3 vault_context.py --quiet        # no output if vault not configured

Exit codes:
    0 = success (even if vault not configured — that's not an error)
    1 = unexpected failure (vault_lib import issue, etc.)
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from vault_lib import get_vault_path, read_file, list_files  # noqa: E402


# Files to load, in order. Each entry: (relative_path, display_label)
# Order matters — this is the order IRIS sees them in her context.
IDENTITY_FILES = [
    ("index.md", "Vault Index (navigation map)"),
    ("me.md", "Me (identity)"),
    ("my-everest.md", "My Everest (3-5 year north star)"),
    ("my-business.md", "My Business (current focus)"),
    ("my-voice.md", "My Voice (how I communicate)"),
    ("maps/iris-rules.md", "IRIS Rules (how I want IRIS to behave)"),
]


def load_identity_files(vault_path: Path) -> list:
    """Load each identity file. Returns list of dicts with file, label, content, found."""
    results = []
    for rel_path, label in IDENTITY_FILES:
        content, err = read_file(rel_path)
        results.append({
            "file": rel_path,
            "label": label,
            "found": content is not None,
            "content": content,
            "error": err,
        })
    return results


def load_most_recent_calendar(vault_path: Path) -> dict:
    """Find and read the most recent Calendar/*.md file (by filename sort).

    Returns dict with file, found, content. Returns {found: False} if empty.
    """
    files, err = list_files(subfolder="Calendar", pattern="*.md")
    if err or not files:
        return {"found": False, "file": None, "content": None, "error": err}

    # Filenames are YYYY-MM-DD.md — lexicographic sort == chronological sort
    most_recent = sorted(files)[-1]
    content, err = read_file(most_recent)
    return {
        "found": content is not None,
        "file": most_recent,
        "content": content,
        "error": err,
    }


def format_as_markdown(status: str, vault_path, identity_results, calendar_result) -> str:
    """Render the loaded context as a single markdown document for IRIS."""
    lines = []
    lines.append("# IRIS Vault Context")
    lines.append("")

    if status != "loaded":
        lines.append(f"_Vault context unavailable: {status}._")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"_Loaded from vault: `{vault_path}`_")
    lines.append("")
    lines.append(
        "The following is the user's own second brain. Treat identity files "
        "(`me.md`, `my-everest.md`, `my-business.md`, `my-voice.md`) as the "
        "authoritative source of truth about who the user is and what they "
        "care about. Treat `maps/iris-rules.md` as the user's explicit "
        "instructions for how IRIS should behave. Respect both."
    )
    lines.append("")

    # Identity files
    for entry in identity_results:
        lines.append(f"## {entry['label']}")
        lines.append(f"_Source: `{entry['file']}`_")
        lines.append("")
        if entry["found"]:
            lines.append(entry["content"].rstrip())
        else:
            lines.append(f"_(Not found: {entry['error']})_")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Most recent calendar entry for continuity
    if calendar_result.get("found"):
        lines.append(f"## Most Recent Daily Note")
        lines.append(f"_Source: `{calendar_result['file']}`_")
        lines.append("")
        lines.append(calendar_result["content"].rstrip())
        lines.append("")
    else:
        lines.append("## Most Recent Daily Note")
        lines.append("_(No daily notes yet — this is a new vault or today's the first day.)_")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Load vault context for IRIS at session start.")
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Produce no output if vault is not configured",
    )
    args = parser.parse_args()

    vault_path = get_vault_path()

    # Case 1: vault not configured
    if vault_path is None:
        if args.quiet:
            sys.exit(0)
        if args.format == "json":
            print(json.dumps({
                "status": "not_configured",
                "message": "IRIS_VAULT_PATH is not set in .env",
                "vault_path": None,
                "identity": [],
                "calendar": None,
            }, indent=2))
        else:
            print(format_as_markdown("not configured (IRIS_VAULT_PATH is not set)", None, [], {}))
        sys.exit(0)

    # Case 2: vault path set but doesn't exist
    if not vault_path.exists():
        if args.quiet:
            sys.exit(0)
        if args.format == "json":
            print(json.dumps({
                "status": "path_missing",
                "message": f"vault path does not exist: {vault_path}",
                "vault_path": str(vault_path),
                "identity": [],
                "calendar": None,
            }, indent=2))
        else:
            print(format_as_markdown(
                f"path does not exist ({vault_path})",
                vault_path, [], {},
            ))
        sys.exit(0)

    # Case 3: vault is there — load identity + calendar
    identity_results = load_identity_files(vault_path)
    calendar_result = load_most_recent_calendar(vault_path)

    files_found = sum(1 for r in identity_results if r["found"])

    if args.format == "json":
        print(json.dumps({
            "status": "loaded",
            "vault_path": str(vault_path),
            "identity_files_found": files_found,
            "identity": identity_results,
            "calendar": calendar_result,
        }, indent=2))
    else:
        print(format_as_markdown("loaded", vault_path, identity_results, calendar_result))

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Unexpected failure — never leak stack traces to IRIS's context
        print(json.dumps({
            "status": "error",
            "error": str(e),
        }), file=sys.stderr)
        sys.exit(1)
