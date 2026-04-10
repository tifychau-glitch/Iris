#!/usr/bin/env python3
"""
Vault Read — read files from the user's Obsidian vault.

Usage:
    python3 vault_read.py --file me.md
    python3 vault_read.py --list
    python3 vault_read.py --list --subfolder Efforts
    python3 vault_read.py --file me.md --format json
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from vault_lib import read_file, list_files, get_vault_path  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Read files from the vault.")
    parser.add_argument("--file", help="Relative path of a file to read")
    parser.add_argument("--list", action="store_true", help="List all markdown files")
    parser.add_argument("--subfolder", help="Limit --list to a subfolder")
    parser.add_argument("--pattern", default="*.md", help="Glob pattern for --list (default: *.md)")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    if not args.file and not args.list:
        parser.error("provide either --file or --list")

    if args.file and args.list:
        parser.error("use --file OR --list, not both")

    # Handle --list
    if args.list:
        files, err = list_files(subfolder=args.subfolder, pattern=args.pattern)
        if err:
            _emit_error(err, args.format)
            sys.exit(1)

        vault = get_vault_path()
        if args.format == "json":
            print(json.dumps({
                "success": True,
                "vault": str(vault) if vault else None,
                "count": len(files),
                "files": files,
            }, indent=2))
        else:
            for f in files:
                print(f)
            if not files:
                print("(no files found)")
        sys.exit(0)

    # Handle --file
    content, err = read_file(args.file)
    if err:
        _emit_error(err, args.format)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps({
            "success": True,
            "file": args.file,
            "content": content,
        }, indent=2))
    else:
        print(content)
    sys.exit(0)


def _emit_error(err, fmt):
    if fmt == "json":
        print(json.dumps({"success": False, "error": err}, indent=2))
    else:
        print(f"Error: {err}", file=sys.stderr)


if __name__ == "__main__":
    main()
