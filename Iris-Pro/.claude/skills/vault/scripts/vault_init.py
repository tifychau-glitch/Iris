#!/usr/bin/env python3
"""
Vault Init — scaffold a starter Obsidian vault at the given path.

Creates the folder structure and writes starter files from templates.
Refuses to scaffold into a folder that already contains `.md` files.

Usage:
    python3 vault_init.py /path/to/vault
    python3 vault_init.py /path/to/vault --force
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR.parent / "templates"

# Folders to create inside the vault (empty is fine)
VAULT_FOLDERS = ["maps", "Calendar", "Efforts", "Atlas", "Concepts"]

# Files to copy from templates/ to the vault root (or into a subfolder)
# Each entry: (template_relative_path, vault_relative_path)
TEMPLATE_FILES = [
    ("me.md", "me.md"),
    ("my-everest.md", "my-everest.md"),
    ("my-voice.md", "my-voice.md"),
    ("my-business.md", "my-business.md"),
    ("index.md", "index.md"),
    ("README.md", "README.md"),
    ("maps/vault-map.md", "maps/vault-map.md"),
    ("maps/iris-rules.md", "maps/iris-rules.md"),
]


def has_markdown_files(path: Path) -> bool:
    """Return True if path contains any .md files (recursively)."""
    return any(path.rglob("*.md"))


def scaffold_vault(vault_path: Path, force: bool = False) -> dict:
    """Create the vault structure at `vault_path`.

    Returns a result dict: {success: bool, message: str, path: str, ...}
    """
    vault_path = vault_path.expanduser().resolve()

    # Safety: don't clobber existing vaults
    if vault_path.exists() and vault_path.is_file():
        return {
            "success": False,
            "error": f"target path is a file, not a directory: {vault_path}",
        }

    if vault_path.exists() and has_markdown_files(vault_path) and not force:
        return {
            "success": False,
            "error": (
                f"vault path already contains markdown files: {vault_path}. "
                f"Pick a different path, or pass --force to scaffold anyway "
                f"(existing files will NOT be overwritten)."
            ),
        }

    # Create the vault root
    try:
        vault_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"success": False, "error": f"could not create vault folder: {e}"}

    # Create subfolders
    for folder in VAULT_FOLDERS:
        try:
            (vault_path / folder).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"success": False, "error": f"could not create {folder}: {e}"}

    # Copy template files (never overwrite existing files)
    created = []
    skipped = []
    for tmpl_rel, vault_rel in TEMPLATE_FILES:
        tmpl_path = TEMPLATES_DIR / tmpl_rel
        target_path = vault_path / vault_rel

        if not tmpl_path.exists():
            return {
                "success": False,
                "error": f"template not found: {tmpl_path}",
            }

        if target_path.exists():
            skipped.append(vault_rel)
            continue

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(tmpl_path.read_text(encoding="utf-8"), encoding="utf-8")
            created.append(vault_rel)
        except OSError as e:
            return {"success": False, "error": f"could not write {vault_rel}: {e}"}

    return {
        "success": True,
        "path": str(vault_path),
        "folders": VAULT_FOLDERS,
        "files_created": created,
        "files_skipped": skipped,
        "message": (
            f"Scaffolded vault at {vault_path}. "
            f"Created {len(created)} files, skipped {len(skipped)} existing."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Scaffold a starter Obsidian vault.")
    parser.add_argument("path", help="Absolute path where the vault should be created")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Scaffold even if the target folder already contains .md files",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    result = scaffold_vault(Path(args.path), force=args.force)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(result["message"])
            print(f"Folders: {', '.join(result['folders'])}")
            print(f"Files created: {len(result['files_created'])}")
            if result["files_skipped"]:
                print(f"Files skipped (already existed): {len(result['files_skipped'])}")
        else:
            print(f"Error: {result.get('error', 'unknown error')}", file=sys.stderr)

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
