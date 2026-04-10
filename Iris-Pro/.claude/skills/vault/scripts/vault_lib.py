"""
Vault Library — shared helpers for reading and writing the user's Obsidian vault.

The vault lives outside the Iris project (e.g., ~/Documents/Iris Vault). Its
location is stored in the IRIS_VAULT_PATH env var. All vault operations are
anchored to that path and reject path traversal.

Design principles:
- Append-only for reserved sections (user content is never touched).
- Refuse to overwrite existing files by default.
- Path traversal is blocked — no `..`, no absolute paths.
- All functions return clear error messages on failure.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Project root discovery (same canonical pattern as memory/telegram skills)
# ---------------------------------------------------------------------------

def _find_project_root():
    """Walk up until we find .env, IRIS.md, or CLAUDE.md."""
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "IRIS.md").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root (looked for .env, IRIS.md, or CLAUDE.md)")


PROJECT_ROOT = _find_project_root()
load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Vault path resolution
# ---------------------------------------------------------------------------

def get_vault_path():
    """Return the configured vault Path, or None if not set or invalid.

    Expands `~` and resolves to absolute path. Does NOT validate existence —
    callers should handle that explicitly so they can offer to scaffold.
    """
    raw = os.getenv("IRIS_VAULT_PATH", "").strip()
    if not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def default_vault_path():
    """Return the default vault location: ~/Documents/Iris Vault."""
    return (Path.home() / "Documents" / "Iris Vault").resolve()


def validate_relative_path(relative_path):
    """Reject path traversal and absolute paths.

    Returns (ok, error_message). If ok is False, error_message explains why.
    """
    if not relative_path:
        return False, "path is empty"
    p = str(relative_path)
    if p.startswith("/") or p.startswith("\\"):
        return False, f"absolute paths not allowed: {p}"
    if ".." in Path(p).parts:
        return False, f"path traversal not allowed: {p}"
    return True, None


# ---------------------------------------------------------------------------
# File read / list
# ---------------------------------------------------------------------------

def read_file(relative_path):
    """Read a file inside the vault. Returns (content, error).

    On success: (content_string, None)
    On failure: (None, error_message)
    """
    vault = get_vault_path()
    if vault is None:
        return None, "IRIS_VAULT_PATH is not set in .env"
    if not vault.exists():
        return None, f"vault path does not exist: {vault}"

    ok, err = validate_relative_path(relative_path)
    if not ok:
        return None, err

    target = (vault / relative_path).resolve()

    # Final containment check — ensure we didn't escape the vault via symlinks
    try:
        target.relative_to(vault)
    except ValueError:
        return None, f"resolved path escapes vault: {target}"

    if not target.exists():
        return None, f"file not found: {relative_path}"
    if not target.is_file():
        return None, f"not a file: {relative_path}"

    try:
        return target.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError) as e:
        return None, f"read failed: {e}"


def list_files(subfolder=None, pattern="*.md"):
    """List markdown files in the vault (or a subfolder). Returns (files, error).

    `files` is a sorted list of paths relative to the vault root.
    """
    vault = get_vault_path()
    if vault is None:
        return None, "IRIS_VAULT_PATH is not set in .env"
    if not vault.exists():
        return None, f"vault path does not exist: {vault}"

    if subfolder:
        ok, err = validate_relative_path(subfolder)
        if not ok:
            return None, err
        base = (vault / subfolder).resolve()
        try:
            base.relative_to(vault)
        except ValueError:
            return None, f"subfolder escapes vault: {base}"
        if not base.exists() or not base.is_dir():
            return None, f"subfolder not found: {subfolder}"
    else:
        base = vault

    matches = sorted(p.relative_to(vault) for p in base.rglob(pattern) if p.is_file())
    return [str(m) for m in matches], None


# ---------------------------------------------------------------------------
# File write / create
# ---------------------------------------------------------------------------

def write_file(relative_path, content, overwrite=False):
    """Write a file inside the vault. Returns (ok, error).

    Refuses to overwrite an existing file unless overwrite=True.
    Creates parent directories as needed.
    """
    vault = get_vault_path()
    if vault is None:
        return False, "IRIS_VAULT_PATH is not set in .env"
    if not vault.exists():
        return False, f"vault path does not exist: {vault}"

    ok, err = validate_relative_path(relative_path)
    if not ok:
        return False, err

    target = (vault / relative_path).resolve()

    try:
        target.relative_to(vault)
    except ValueError:
        return False, f"resolved path escapes vault: {target}"

    if target.exists() and not overwrite:
        return False, f"file already exists (use overwrite=True): {relative_path}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return True, None
    except OSError as e:
        return False, f"write failed: {e}"


def append_to_section(relative_path, section_heading, content):
    """Append content under a `## section_heading` in the file.

    If the file doesn't exist, create it.
    If the section heading doesn't exist, create it at the end of the file.
    The new content is appended below the LAST line of the section's block
    (everything up to the next `## ` or end-of-file), so repeated appends
    stack under the same heading.

    Returns (ok, error).

    This is the "reserved section" contract. User-authored content in OTHER
    sections is never touched. Only the named section is modified.
    """
    vault = get_vault_path()
    if vault is None:
        return False, "IRIS_VAULT_PATH is not set in .env"
    if not vault.exists():
        return False, f"vault path does not exist: {vault}"

    ok, err = validate_relative_path(relative_path)
    if not ok:
        return False, err

    target = (vault / relative_path).resolve()

    try:
        target.relative_to(vault)
    except ValueError:
        return False, f"resolved path escapes vault: {target}"

    # Read existing content, or start fresh
    if target.exists() and target.is_file():
        try:
            existing = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return False, f"read failed: {e}"
    else:
        existing = ""

    heading_line = f"## {section_heading}"
    new_content = _append_under_heading(existing, heading_line, content)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
        return True, None
    except OSError as e:
        return False, f"write failed: {e}"


def _append_under_heading(existing, heading_line, content):
    """Pure string transformation. Returns the new file content.

    Finds `heading_line` in `existing`. If found, inserts `content` at the end
    of that section's block (just before the next `## ` heading or EOF).
    If not found, appends the heading + content to the end of the file.
    """
    lines = existing.splitlines() if existing else []

    # Find the heading line (exact match at line start)
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip() == heading_line:
            heading_idx = i
            break

    if heading_idx is None:
        # No heading found — append at end
        out = existing.rstrip("\n")
        if out:
            out += "\n\n"
        out += f"{heading_line}\n\n{content.rstrip()}\n"
        return out

    # Find the end of this section (next `## ` heading or EOF)
    end_idx = len(lines)
    for i in range(heading_idx + 1, len(lines)):
        if re.match(r"^## [^#]", lines[i]):
            end_idx = i
            break

    # Trim trailing blank lines inside the section, then insert
    section_end = end_idx
    while section_end > heading_idx + 1 and not lines[section_end - 1].strip():
        section_end -= 1

    before = lines[:section_end]
    after = lines[end_idx:]

    # Build the insertion: a blank line, then the content, then a blank line
    new_block = ["", content.rstrip(), ""]

    new_lines = before + new_block + [""] + after if after else before + new_block
    # Clean up: no more than one trailing blank line at EOF
    result = "\n".join(new_lines).rstrip("\n") + "\n"
    return result
