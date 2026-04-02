"""
Script: mem0 Client Factory
Purpose: Initialize and return a configured mem0 Memory instance.
All memory scripts import get_memory_client() and PROJECT_ROOT from here.
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv


def _find_project_root():
    """Walk up from this script's directory until we find .env or CLAUDE.md."""
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root (looked for .env or CLAUDE.md)")


PROJECT_ROOT = _find_project_root()

load_dotenv(PROJECT_ROOT / ".env")

CONFIG_PATH = PROJECT_ROOT / ".claude" / "skills" / "memory" / "references" / "mem0_config.yaml"
HISTORY_DB_PATH = PROJECT_ROOT / "data" / "mem0_history.db"

USER_ID = os.getenv("MEM0_USER_ID", "default_user")
AGENT_ID = "claude_code"

PYTHON_BIN = sys.executable

_client = None


# ---------------------------------------------------------------------------
# Security: Secrets scrubber
# ---------------------------------------------------------------------------

import re as _re

# Patterns that match common secret formats — order matters (most specific first)
_SECRET_PATTERNS = [
    # API keys with known prefixes
    (r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED_SK_KEY]"),
    (r"pk_(?:live|test)_[A-Za-z0-9]{20,}", "[REDACTED_PK_KEY]"),
    (r"sk_(?:live|test)_[A-Za-z0-9]{20,}", "[REDACTED_SK_KEY]"),
    (r"xoxb-[A-Za-z0-9-]{20,}", "[REDACTED_SLACK_TOKEN]"),
    (r"xoxp-[A-Za-z0-9-]{20,}", "[REDACTED_SLACK_TOKEN]"),
    (r"xapp-[A-Za-z0-9-]{20,}", "[REDACTED_SLACK_TOKEN]"),
    (r"ghp_[A-Za-z0-9]{20,}", "[REDACTED_GITHUB_TOKEN]"),
    (r"gho_[A-Za-z0-9]{20,}", "[REDACTED_GITHUB_TOKEN]"),
    (r"ntn_[A-Za-z0-9]{20,}", "[REDACTED_NOTION_TOKEN]"),
    (r"pat[A-Za-z0-9]{20,}", "[REDACTED_PAT]"),
    (r"pplx-[A-Za-z0-9]{20,}", "[REDACTED_PPLX_KEY]"),
    (r"fc-[a-f0-9]{20,}", "[REDACTED_FC_KEY]"),
    (r"pcsk_[A-Za-z0-9_-]{20,}", "[REDACTED_PINECONE_KEY]"),
    (r"AIzaSy[A-Za-z0-9_-]{20,}", "[REDACTED_GOOGLE_KEY]"),
    # Bearer tokens
    (r"Bearer\s+[A-Za-z0-9._-]{20,}", "[REDACTED_BEARER]"),
    # JWTs (three base64 segments separated by dots)
    (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "[REDACTED_JWT]"),
    # Generic long hex/base64 strings after key-like words
    (r"(?i)(?:api[_-]?key|secret|token|password|credential|auth)[\"'\s:=]+[A-Za-z0-9+/=_-]{20,}", "[REDACTED_CREDENTIAL]"),
    # Connection strings
    (r"(?:postgres|mysql|mongodb|redis)://[^\s]{15,}", "[REDACTED_CONN_STRING]"),
]

_compiled_patterns = [(_re.compile(p), r) for p, r in _SECRET_PATTERNS]


def sanitize_text(text):
    """Strip secrets and credentials from text before sending to external APIs.
    Returns the sanitized text. Used by auto_capture.py and mem0_add.py."""
    for pattern, replacement in _compiled_patterns:
        text = pattern.sub(replacement, text)
    return text


def get_memory_client():
    """Return singleton mem0 Memory instance configured from mem0_config.yaml."""
    global _client
    if _client is not None:
        return _client

    from mem0 import Memory

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    config = _resolve_env_vars(config)

    # Override history_db_path with absolute path so it works regardless of cwd
    config["history_db_path"] = str(HISTORY_DB_PATH)

    _client = Memory.from_config(config_dict=config)
    return _client


def _resolve_env_vars(obj):
    """Recursively resolve ${VAR} references in config values."""
    if isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            return os.getenv(var_name, obj)
        return obj
    elif isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    return obj
