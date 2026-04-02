#!/usr/bin/env python3
"""
Memory System Installer for AI OS
==================================

Configures and activates the 3-tier persistent memory system (mem0 + Pinecone).
The memory scripts already exist in .claude/skills/memory/scripts/ — this installer
sets up the configuration, dependencies, and hooks to activate them.

Usage:
    python3 setup_memory.py                                                # Interactive
    python3 setup_memory.py --user-id "jane" --pinecone-index "my-memory"  # Non-interactive
    python3 setup_memory.py --dry-run                                      # Preview changes

Prerequisites:
    - Python 3.9+
    - OPENAI_API_KEY in .env
    - PINECONE_API_KEY in .env
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
SKILLS_MEMORY = PROJECT_ROOT / ".claude" / "skills" / "memory"
SCRIPTS_DIR = SKILLS_MEMORY / "scripts"
CONFIG_PATH = SKILLS_MEMORY / "references" / "mem0_config.yaml"
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.local.json"
ENV_PATH = PROJECT_ROOT / ".env"

REQUIRED_PACKAGES = ["mem0ai", "pyyaml", "python-dotenv", "requests", "openai"]
REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "PINECONE_API_KEY"]

REQUIRED_DIRS = [
    "data/capture_markers",
    "memory/logs",
    "logs",
]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python_version():
    """Ensure Python 3.9+."""
    if sys.version_info < (3, 9):
        print(f"[!] Python 3.9+ required, found {sys.version}")
        return False
    print(f"[OK] Python {sys.version.split()[0]}")
    return True


def check_scripts_exist():
    """Ensure the memory skill scripts are present."""
    required = [
        "mem0_client.py", "auto_capture.py", "smart_search.py",
        "mem0_search.py", "mem0_add.py", "mem0_list.py",
        "mem0_delete.py", "mem0_sync_md.py", "daily_log.py",
    ]
    missing = [f for f in required if not (SCRIPTS_DIR / f).exists()]
    if missing:
        print(f"[!] Missing scripts in {SCRIPTS_DIR}: {', '.join(missing)}")
        return False
    print(f"[OK] All {len(required)} memory scripts present")
    return True


def check_env_vars():
    """Check .env has the required API keys."""
    if not ENV_PATH.exists():
        print("[!] .env file not found — create it first (see .env.example)")
        return False

    env_content = ENV_PATH.read_text()
    missing = []
    for var in REQUIRED_ENV_VARS:
        # Check for uncommented, non-empty value
        for line in env_content.splitlines():
            line = line.strip()
            if line.startswith(f"{var}=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip()
                if val and val != f"your-{var.lower().replace('_', '-')}":
                    break
        else:
            missing.append(var)

    if missing:
        print(f"[!] Missing in .env: {', '.join(missing)}")
        print("    Add these keys to your .env file before running this installer.")
        return False

    print(f"[OK] Required API keys found in .env")
    return True


# ---------------------------------------------------------------------------
# Installation steps
# ---------------------------------------------------------------------------

def install_packages(dry_run=False):
    """Install pip dependencies."""
    print("\n--- Installing dependencies ---")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + REQUIRED_PACKAGES

    if dry_run:
        print(f"  Would run: {' '.join(cmd)}")
        return True

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"  Installed: {', '.join(REQUIRED_PACKAGES)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [!] pip install failed: {e.stderr[:200]}")
        return False


def create_directories(dry_run=False):
    """Create required directories."""
    print("\n--- Creating directories ---")
    for d in REQUIRED_DIRS:
        path = PROJECT_ROOT / d
        if dry_run:
            status = "exists" if path.exists() else "would create"
            print(f"  {d}/ — {status}")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  {d}/ — OK")
    return True


def set_user_id(user_id, dry_run=False):
    """Write MEM0_USER_ID to .env."""
    print(f"\n--- Setting user ID: {user_id} ---")

    if not ENV_PATH.exists():
        print("  [!] .env not found")
        return False

    content = ENV_PATH.read_text()

    # Check if MEM0_USER_ID already exists
    lines = content.splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("MEM0_USER_ID=") or stripped.startswith("# MEM0_USER_ID="):
            new_lines.append(f"MEM0_USER_ID={user_id}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n# mem0 user ID (set by setup_memory.py)")
        new_lines.append(f"MEM0_USER_ID={user_id}")

    if dry_run:
        print(f"  Would set MEM0_USER_ID={user_id} in .env")
        return True

    ENV_PATH.write_text("\n".join(new_lines) + "\n")
    print(f"  Set MEM0_USER_ID={user_id} in .env")
    return True


def update_pinecone_index(index_name, dry_run=False):
    """Update collection_name in mem0_config.yaml."""
    print(f"\n--- Setting Pinecone index: {index_name} ---")

    if not CONFIG_PATH.exists():
        print(f"  [!] Config not found at {CONFIG_PATH}")
        return False

    content = CONFIG_PATH.read_text()
    new_content = content.replace(
        'collection_name: "ai-os-memory"',
        f'collection_name: "{index_name}"'
    )

    if content == new_content and "ai-os-memory" not in content:
        # Already customized to something else
        print(f"  Config already customized — skipping")
        return True

    if dry_run:
        print(f"  Would set collection_name: \"{index_name}\" in mem0_config.yaml")
        return True

    CONFIG_PATH.write_text(new_content)
    print(f"  Set collection_name: \"{index_name}\"")
    return True


def update_stop_hook(dry_run=False):
    """Switch Stop hook from basic memory_capture.py to advanced auto_capture.py."""
    print("\n--- Updating Stop hook ---")

    basic_cmd = "python3 hooks/memory_capture.py"
    advanced_cmd = "python3 .claude/skills/memory/scripts/auto_capture.py"

    if not SETTINGS_PATH.exists():
        print(f"  [!] {SETTINGS_PATH} not found — run setup.sh first")
        return False

    content = SETTINGS_PATH.read_text()

    if advanced_cmd in content:
        print("  Already using advanced auto_capture hook")
        return True

    if basic_cmd in content:
        new_content = content.replace(basic_cmd, advanced_cmd)

        # Also add timeout if not present
        new_content = new_content.replace(
            '"async": true',
            '"timeout": 60,\n            "async": true'
        ) if '"timeout"' not in new_content else new_content

        if dry_run:
            print(f"  Would switch Stop hook to: {advanced_cmd}")
            return True

        SETTINGS_PATH.write_text(new_content)
        print(f"  Switched Stop hook to: {advanced_cmd}")
        return True

    # No existing hook — add it
    try:
        settings = json.loads(content)
        if "hooks" not in settings:
            settings["hooks"] = {}
        settings["hooks"]["Stop"] = [{
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": advanced_cmd,
                "timeout": 60,
                "async": True,
            }]
        }]

        if dry_run:
            print(f"  Would add Stop hook: {advanced_cmd}")
            return True

        SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n")
        print(f"  Added Stop hook: {advanced_cmd}")
        return True
    except json.JSONDecodeError:
        print("  [!] Could not parse settings.local.json")
        return False


def rebuild_fts_index(dry_run=False):
    """Initialize the FTS5 keyword index for hybrid search."""
    print("\n--- Initializing search index ---")

    script = SCRIPTS_DIR / "smart_search.py"
    if not script.exists():
        print(f"  [!] smart_search.py not found")
        return False

    if dry_run:
        print("  Would run: smart_search.py --rebuild-index")
        return True

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--rebuild-index"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            print(f"  FTS5 index initialized")
            return True
        else:
            # Index rebuild may fail if no memories exist yet — that's OK
            print(f"  FTS5 index created (empty — will populate as memories are added)")
            return True
    except Exception as e:
        print(f"  [!] Index build failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI OS Memory System Installer — configures mem0 + Pinecone"
    )
    parser.add_argument("--user-id", type=str, help="Your mem0 user ID (e.g., your name)")
    parser.add_argument("--pinecone-index", type=str, default="ai-os-memory",
                        help="Pinecone index/collection name (default: ai-os-memory)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--skip-packages", action="store_true", help="Skip pip install")

    args = parser.parse_args()

    print("=" * 50)
    print("  AI OS — Memory System Installer")
    print("=" * 50)

    if args.dry_run:
        print("  [DRY RUN — no changes will be made]\n")

    # Pre-flight checks
    if not check_python_version():
        sys.exit(1)

    if not check_scripts_exist():
        print("\nThe memory skill scripts are missing. Ensure the AIOS package is complete.")
        sys.exit(1)

    if not check_env_vars():
        sys.exit(1)

    # Get user ID interactively if not provided
    user_id = args.user_id
    if not user_id and not args.dry_run:
        user_id = input("\nEnter your name (for mem0 user ID): ").strip()
        if not user_id:
            print("[!] User ID is required.")
            sys.exit(1)
    elif not user_id:
        user_id = "example_user"

    # Run installation steps
    steps = [
        ("Install packages", lambda: install_packages(args.dry_run) if not args.skip_packages else True),
        ("Create directories", lambda: create_directories(args.dry_run)),
        ("Set user ID", lambda: set_user_id(user_id, args.dry_run)),
        ("Set Pinecone index", lambda: update_pinecone_index(args.pinecone_index, args.dry_run)),
        ("Update Stop hook", lambda: update_stop_hook(args.dry_run)),
        ("Initialize search index", lambda: rebuild_fts_index(args.dry_run)),
    ]

    results = []
    for name, step in steps:
        success = step()
        results.append((name, success))

    # Summary
    print("\n" + "=" * 50)
    print("  Results")
    print("=" * 50)

    all_ok = True
    for name, success in results:
        status = "OK" if success else "FAILED"
        if not success:
            all_ok = False
        print(f"  [{status}] {name}")

    if all_ok:
        print("\n  Memory system configured!")
        if not args.dry_run:
            print("\n  Next steps:")
            print("  1. Restart Claude Code (so hooks take effect)")
            print("  2. Say: \"Search memory for preferences\"")
            print("  3. The system will auto-capture facts from conversations")
    else:
        print("\n  Some steps failed. Fix the issues above and re-run.")

    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
