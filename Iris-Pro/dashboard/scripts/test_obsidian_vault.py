#!/usr/bin/env python3
"""Test the Obsidian Vault connection.

On "Test" click from the dashboard card:
- If the path is blank → use default (~/Documents/Iris Vault)
- If the path doesn't exist → scaffold a new vault there
- If the path exists and is empty → scaffold into it
- If the path exists and has .md files → validate read access, report success
- If the path exists but isn't a directory → error

Always returns JSON to stdout.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def emit(result: dict):
    print(json.dumps(result))
    sys.exit(0 if result.get("success") else 0)  # exit 0 so dashboard always parses JSON


def default_vault_path() -> Path:
    return (Path.home() / "Documents" / "Iris Vault").resolve()


def resolve_vault_path(raw: str) -> Path:
    """Resolve the user's input to an absolute Path. Handles blank, ~, relative."""
    if not raw or raw.strip() == "":
        return default_vault_path()
    return Path(raw.strip()).expanduser().resolve()


def has_markdown_files(path: Path) -> bool:
    try:
        return any(path.rglob("*.md"))
    except OSError:
        return False


def count_markdown_files(path: Path) -> int:
    try:
        return sum(1 for _ in path.rglob("*.md"))
    except OSError:
        return 0


def scaffold_vault(vault_path: Path) -> dict:
    """Invoke vault_init.py to scaffold the starter vault."""
    project_root = Path(__file__).parent.parent.parent.resolve()
    vault_init = project_root / ".claude" / "skills" / "vault" / "scripts" / "vault_init.py"

    if not vault_init.exists():
        return {"success": False, "error": f"vault_init.py not found at {vault_init}"}

    try:
        proc = subprocess.run(
            [sys.executable, str(vault_init), str(vault_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "vault scaffolding timed out"}
    except Exception as e:
        return {"success": False, "error": f"failed to run vault_init.py: {e}"}

    # vault_init.py prints JSON to stdout
    try:
        return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {
            "success": False,
            "error": f"vault_init returned no output (stderr: {proc.stderr[:200]})",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": f"vault_init output was not JSON: {proc.stdout[:200]}",
        }


def main():
    # Load .env using the same pattern as other test scripts
    env_path = os.environ.get(
        "DOTENV_PATH",
        str(Path(__file__).parent.parent.parent / ".env"),
    )
    load_dotenv(env_path)

    raw = os.getenv("IRIS_VAULT_PATH", "").strip()
    vault_path = resolve_vault_path(raw)

    # Case 1: path exists and is a file (not a directory) → hard error
    if vault_path.exists() and vault_path.is_file():
        emit({
            "success": False,
            "error": f"Path is a file, not a folder: {vault_path}",
        })

    # Case 2: path doesn't exist → scaffold
    if not vault_path.exists():
        result = scaffold_vault(vault_path)
        if not result.get("success"):
            emit({
                "success": False,
                "error": f"Could not scaffold vault at {vault_path}: {result.get('error', 'unknown')}",
            })
        emit({
            "success": True,
            "message": (
                f"Scaffolded a new vault at {vault_path}. "
                f"Open Obsidian, choose 'Open folder as vault', and select this folder."
            ),
        })

    # Case 3: path exists and is a directory
    if not os.access(vault_path, os.R_OK) or not os.access(vault_path, os.W_OK):
        emit({
            "success": False,
            "error": f"Vault folder is not readable/writable: {vault_path}",
        })

    # Case 3a: empty folder → scaffold into it
    if not has_markdown_files(vault_path):
        result = scaffold_vault(vault_path)
        if not result.get("success"):
            emit({
                "success": False,
                "error": f"Could not scaffold into empty folder {vault_path}: {result.get('error', 'unknown')}",
            })
        emit({
            "success": True,
            "message": (
                f"Scaffolded starter vault in {vault_path}. "
                f"Open Obsidian and point it at this folder."
            ),
        })

    # Case 3b: folder has .md files → treat as existing vault, don't scaffold
    count = count_markdown_files(vault_path)
    emit({
        "success": True,
        "message": (
            f"Connected to vault at {vault_path}. Found {count} markdown file"
            f"{'s' if count != 1 else ''}."
        ),
    })


if __name__ == "__main__":
    main()
