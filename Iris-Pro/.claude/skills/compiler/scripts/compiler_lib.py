"""
Compiler Library — shared helpers for the compiler skill.

Storage: data/compiler_proposals.db (SQLite, auto-created on first run).

Proposal lifecycle:
    pending → approved → applied
    pending → rejected

A proposal is a single suggested update to the vault. Types:
    - new_concept       — create a new file in Concepts/
    - append_to_effort  — append content under a reserved section in Efforts/
    - observation       — a flagged gap between aspiration (vault) and behavior (journal)
                          — surfaced for user review only, not directly applied
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Find project root via the same pattern vault_lib uses
def _find_project_root():
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "IRIS.md").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = _find_project_root()
DB_PATH = PROJECT_ROOT / "data" / "compiler_proposals.db"

VALID_TYPES = {"new_concept", "append_to_effort", "observation"}
VALID_STATUSES = {"pending", "approved", "rejected", "applied"}


def _ensure_data_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize the proposals database. Idempotent."""
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            run_id TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('new_concept', 'append_to_effort', 'observation')),
            target_file TEXT,
            section TEXT,
            title TEXT,
            content TEXT NOT NULL,
            reasoning TEXT,
            source_entries TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'approved', 'rejected', 'applied')),
            decided_at TEXT,
            applied_at TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_proposals_run_id ON proposals(run_id)")
    conn.commit()
    return conn


def add_proposal(conn, run_id: str, proposal: dict):
    """Insert a single proposal. Returns the new row id.

    `proposal` is a dict with keys: type, target_file, section, title,
    content, reasoning, source_entries (list).
    """
    ptype = proposal.get("type")
    if ptype not in VALID_TYPES:
        raise ValueError(f"invalid proposal type: {ptype}")

    now = datetime.now().isoformat()
    source_entries = proposal.get("source_entries") or []
    if not isinstance(source_entries, (list, tuple)):
        source_entries = [source_entries]

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO proposals (
            created_at, run_id, type, target_file, section, title,
            content, reasoning, source_entries, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (
        now,
        run_id,
        ptype,
        proposal.get("target_file"),
        proposal.get("section"),
        proposal.get("title"),
        proposal.get("content", "").strip(),
        proposal.get("reasoning", "").strip(),
        json.dumps(source_entries),
    ))
    conn.commit()
    return cur.lastrowid


def list_proposals(status: str = None, run_id: str = None, limit: int = 50):
    """Return a list of proposals as dicts. Filter by status or run_id."""
    conn = init_db()
    cur = conn.cursor()
    query = "SELECT * FROM proposals"
    params = []
    where = []
    if status:
        where.append("status = ?")
        params.append(status)
    if run_id:
        where.append("run_id = ?")
        params.append(run_id)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        try:
            r["source_entries"] = json.loads(r["source_entries"] or "[]")
        except json.JSONDecodeError:
            r["source_entries"] = []
    conn.close()
    return rows


def get_proposal(proposal_id: int):
    """Return a single proposal dict, or None."""
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    try:
        result["source_entries"] = json.loads(result["source_entries"] or "[]")
    except json.JSONDecodeError:
        result["source_entries"] = []
    return result


def set_status(proposal_id: int, status: str, applied: bool = False):
    """Update a proposal's status. Sets decided_at, and applied_at if applied=True."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")

    now = datetime.now().isoformat()
    conn = init_db()
    cur = conn.cursor()
    if applied:
        cur.execute(
            "UPDATE proposals SET status = ?, applied_at = ? WHERE id = ?",
            (status, now, proposal_id),
        )
    else:
        cur.execute(
            "UPDATE proposals SET status = ?, decided_at = ? WHERE id = ?",
            (status, now, proposal_id),
        )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0
