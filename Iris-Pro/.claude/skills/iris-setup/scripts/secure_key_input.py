#!/usr/bin/env python3
"""
IRIS Setup — Environment File Manager

Prepares the .env file for key entry and validates that keys have been added.
Users paste their keys directly into the .env file using their editor.

Usage:
    python3 secure_key_input.py --setup        # Create .env from template
    python3 secure_key_input.py --check KEY    # Check if a specific key is set
    python3 secure_key_input.py --check-all    # Check all required keys
"""

import sys
import os
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
ENV_EXAMPLE = os.path.join(PROJECT_ROOT, ".env.example")

REQUIRED_KEYS = {
    "ANTHROPIC_API_KEY": {
        "label": "Anthropic API Key",
        "validate": lambda v: v.startswith("sk-ant-"),
        "hint": "Should start with sk-ant-",
    },
    "PINECONE_API_KEY": {
        "label": "Pinecone API Key",
        "validate": lambda v: len(v) > 10,
        "hint": "Should be a long alphanumeric string",
    },
    "TELEGRAM_BOT_TOKEN": {
        "label": "Telegram Bot Token",
        "validate": lambda v: ":" in v,
        "hint": "Should look like 123456789:ABCdefGHI...",
    },
}


def setup_env():
    """Create .env from .env.example if it doesn't exist."""
    if os.path.exists(ENV_FILE):
        print(f"EXISTS: .env file already exists at {ENV_FILE}")
        return

    if os.path.exists(ENV_EXAMPLE):
        with open(ENV_EXAMPLE, "r") as src, open(ENV_FILE, "w") as dst:
            dst.write(src.read())
        print(f"CREATED: .env file created from template at {ENV_FILE}")
    else:
        with open(ENV_FILE, "w") as f:
            f.write("# IRIS Environment Variables\n\n")
            for key_name, info in REQUIRED_KEYS.items():
                f.write(f"# {info['label']}\n")
                f.write(f"{key_name}=\n\n")
        print(f"CREATED: .env file created at {ENV_FILE}")


def read_env_value(key_name):
    """Read a key's value from the .env file."""
    if not os.path.exists(ENV_FILE):
        return None

    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key_name}="):
                value = line[len(key_name) + 1:].strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                return value if value else None
    return None


def check_key(key_name):
    """Check if a key exists and passes validation."""
    value = read_env_value(key_name)

    if value is None:
        info = REQUIRED_KEYS.get(key_name, {})
        label = info.get("label", key_name)
        print(f"MISSING: {label} is not set in .env")
        return False

    info = REQUIRED_KEYS.get(key_name, {})
    validator = info.get("validate")

    if validator and not validator(value):
        label = info.get("label", key_name)
        hint = info.get("hint", "Check the format")
        print(f"INVALID: {label} doesn't look right. {hint}")
        return False

    label = info.get("label", key_name)
    print(f"OK: {label} is configured")
    return True


def check_all():
    """Check all required keys and report status."""
    results = {}
    for key_name in REQUIRED_KEYS:
        results[key_name] = check_key(key_name)

    configured = sum(1 for v in results.values() if v)
    total = len(REQUIRED_KEYS)
    print(f"\n{configured}/{total} required keys configured.")

    if configured == total:
        print("ALL_SET: Ready to go.")
        return True
    else:
        missing = [k for k, v in results.items() if not v]
        print(f"NEED: {', '.join(missing)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="IRIS .env setup and validation")
    parser.add_argument("--setup", action="store_true", help="Create .env from template")
    parser.add_argument("--check", metavar="KEY", help="Check if a specific key is configured")
    parser.add_argument("--check-all", action="store_true", help="Check all required keys")
    args = parser.parse_args()

    if args.setup:
        setup_env()
    elif args.check:
        success = check_key(args.check)
        sys.exit(0 if success else 1)
    elif args.check_all:
        success = check_all()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
