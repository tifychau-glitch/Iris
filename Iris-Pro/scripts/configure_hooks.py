#!/usr/bin/env python3
"""
Configure Hooks — safely merge hooks into settings.local.json.

Preserves all existing content (permissions, etc.) and adds the hooks
block if it's missing. Idempotent — safe to run multiple times.

Usage:
    python3 scripts/configure_hooks.py              # apply
    python3 scripts/configure_hooks.py --dry-run    # preview changes
    python3 scripts/configure_hooks.py --check      # exit 0 if hooks present, 1 if missing
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.local.json"

# The standard hooks every IRIS install should have
STANDARD_HOOKS = {
    "Stop": [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 .claude/hooks/memory_capture.py",
                    "async": True,
                }
            ],
        }
    ],
    "PreToolUse": [
        {
            "matcher": "Bash",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 .claude/hooks/guardrail_check.py",
                }
            ],
        }
    ],
    "PostToolUse": [
        {
            "matcher": "Bash",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 .claude/hooks/validate_output.py",
                }
            ],
        }
    ],
}


def load_settings():
    """Load existing settings, or return minimal dict if file doesn't exist."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not parse {SETTINGS_PATH}: {e}", file=sys.stderr)
        return {}


def hooks_present(settings: dict) -> bool:
    """Return True if the hooks key exists and has content."""
    return bool(settings.get("hooks"))


def merge_hooks(settings: dict) -> dict:
    """Add standard hooks to settings if missing. Returns the updated dict."""
    if hooks_present(settings):
        return settings  # already configured, don't clobber
    settings["hooks"] = STANDARD_HOOKS
    return settings


def save_settings(settings: dict):
    """Write settings back to disk with clean formatting."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Configure IRIS hooks in settings.local.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--check", action="store_true", help="Check if hooks are present (exit 0/1)")
    args = parser.parse_args()

    settings = load_settings()

    if args.check:
        if hooks_present(settings):
            print("Hooks are configured.")
            sys.exit(0)
        else:
            print("Hooks are NOT configured.")
            sys.exit(1)

    if hooks_present(settings):
        print("Hooks already configured — no changes needed.")
        sys.exit(0)

    updated = merge_hooks(settings)

    if args.dry_run:
        print("Would add hooks to settings.local.json:")
        print(json.dumps(updated.get("hooks", {}), indent=2))
        print(f"\nPermissions preserved: {len(updated.get('permissions', {}).get('allow', []))} rules")
        sys.exit(0)

    save_settings(updated)
    perm_count = len(updated.get("permissions", {}).get("allow", []))
    print(f"Hooks configured in {SETTINGS_PATH}")
    print(f"  Stop hook: memory_capture.py (async)")
    print(f"  PreToolUse hook: guardrail_check.py")
    print(f"  PostToolUse hook: validate_output.py")
    print(f"  Permissions preserved: {perm_count} rules")


if __name__ == "__main__":
    main()
