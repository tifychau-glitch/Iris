#!/usr/bin/env python3
"""
Vault Write — append or create files in the user's Obsidian vault.

Usage:
    # Append content under a reserved heading in a file (creates file if missing)
    python3 vault_write.py --append --file Calendar/2026-04-09.md \
        --section "Iris Check-ins" --content "What's the one thing today?"

    # Create a new file (refuses to overwrite existing)
    python3 vault_write.py --create --file Concepts/shipping-patterns.md \
        --content "# Shipping Patterns\n..."

    # Force overwrite an existing file (use sparingly)
    python3 vault_write.py --create --file me.md --content "..." --overwrite
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from vault_lib import write_file, append_to_section  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Write files in the vault.")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--append", action="store_true", help="Append to a section in a file")
    mode.add_argument("--create", action="store_true", help="Create a new file")

    parser.add_argument("--file", required=True, help="Vault-relative file path")
    parser.add_argument("--content", required=True, help="Content to write (literal string)")
    parser.add_argument("--section", help="Section heading (required for --append)")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwrite on --create")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    if args.append and not args.section:
        parser.error("--append requires --section")

    # Unescape common shell-friendly sequences in --content
    content = args.content.replace("\\n", "\n").replace("\\t", "\t")

    if args.append:
        ok, err = append_to_section(args.file, args.section, content)
        action = "append"
    else:
        ok, err = write_file(args.file, content, overwrite=args.overwrite)
        action = "create"

    if not ok:
        if args.format == "json":
            print(json.dumps({"success": False, "error": err, "action": action}, indent=2))
        else:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps({
            "success": True,
            "action": action,
            "file": args.file,
            "section": args.section if args.append else None,
        }, indent=2))
    else:
        msg = f"Appended to {args.file} under '{args.section}'" if args.append else f"Created {args.file}"
        print(msg)
    sys.exit(0)


if __name__ == "__main__":
    main()
