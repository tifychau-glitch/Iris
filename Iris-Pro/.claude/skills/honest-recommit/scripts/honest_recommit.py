"""
Tool: Honest Re-Commitment
Purpose: Track commitments the user makes with target dates, count slips
         (postponements / misses), and surface ONE soft question after the
         third slip — never more than once per conversation, never as a nag.
Usage: python3 scripts/honest_recommit.py <command> [options]

Commands:
  capture    Capture a new commitment
  find       Search existing commitments (for dedup)
  slip       Record a slip (postponement or miss)
  recommit   Reset slip counter after user reaffirms commitment
  complete   Mark a commitment as completed
  archive    Archive a commitment (user let it go)
  list       List commitments by status

Principles:
  - Silent capture
  - Surface at slip_count == 3, exactly once
  - After 2 full re-commit cycles, stop auto-surfacing
  - One per conversation, session-scoped
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "commitments.db"
SESSION_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / ".honest_recommit_session.json"

SLIP_THRESHOLD = 3
MAX_RECOMMIT_CYCLES = 2
SESSION_TIMEOUT_HOURS = 6


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            original_target_date TEXT,
            current_target_date TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','completed','archived','stopped_asking')),
            slip_count INTEGER NOT NULL DEFAULT 0,
            last_slip_at TEXT,
            recommit_cycles INTEGER NOT NULL DEFAULT 0,
            last_surfaced_at TEXT,
            archived_reason TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS slip_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commitment_id INTEGER NOT NULL,
            slipped_at TEXT NOT NULL,
            old_target_date TEXT,
            new_target_date TEXT,
            reason TEXT,
            FOREIGN KEY (commitment_id) REFERENCES commitments(id)
        )
    """)
    conn.commit()
    return conn


def load_session():
    if not SESSION_PATH.exists():
        return {"last_active": None, "surfaced_ids": []}
    try:
        data = json.loads(SESSION_PATH.read_text())
        last = data.get("last_active")
        if last:
            last_dt = datetime.fromisoformat(last)
            if datetime.now() - last_dt > timedelta(hours=SESSION_TIMEOUT_HOURS):
                return {"last_active": None, "surfaced_ids": []}
        return data
    except Exception:
        return {"last_active": None, "surfaced_ids": []}


def save_session(session):
    session["last_active"] = datetime.now().isoformat()
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(json.dumps(session))


def capture_commitment(title, original_text, target_date):
    conn = init_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO commitments
            (title, original_text, created_at, original_target_date, current_target_date, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (title, original_text, now, target_date, target_date),
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return {"captured": True, "id": cid, "title": title, "target_date": target_date}


def find_commitments(query):
    conn = init_db()
    cur = conn.cursor()
    like = f"%{query.lower()}%"
    cur.execute(
        """
        SELECT * FROM commitments
        WHERE status IN ('active','stopped_asking')
        AND (LOWER(title) LIKE ? OR LOWER(original_text) LIKE ?)
        ORDER BY created_at DESC
        """,
        (like, like),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"query": query, "matches": rows}


def slip_commitment(commitment_id, new_target_date, reason):
    conn = init_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"slipped": False, "error": "commitment not found"}

    now = datetime.now().isoformat()
    old_target = row["current_target_date"]
    new_slip_count = row["slip_count"] + 1

    cur.execute(
        """
        INSERT INTO slip_history (commitment_id, slipped_at, old_target_date, new_target_date, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (commitment_id, now, old_target, new_target_date, reason),
    )

    cur.execute(
        """
        UPDATE commitments
        SET slip_count = ?, last_slip_at = ?, current_target_date = COALESCE(?, current_target_date)
        WHERE id = ?
        """,
        (new_slip_count, now, new_target_date, commitment_id),
    )
    conn.commit()

    # Determine if we should surface
    should_surface = False
    session = load_session()
    surfaced_session = set(session.get("surfaced_ids", []))

    if (
        new_slip_count >= SLIP_THRESHOLD
        and row["status"] == "active"
        and row["recommit_cycles"] < MAX_RECOMMIT_CYCLES
        and commitment_id not in surfaced_session
    ):
        should_surface = True
        cur.execute(
            "UPDATE commitments SET last_surfaced_at = ? WHERE id = ?",
            (now, commitment_id),
        )
        conn.commit()
        surfaced_session.add(commitment_id)
        session["surfaced_ids"] = list(surfaced_session)
        save_session(session)

    cur.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,))
    updated = dict(cur.fetchone())
    conn.close()

    return {
        "slipped": True,
        "id": commitment_id,
        "slip_count": new_slip_count,
        "should_surface": should_surface,
        "is_repeat_question": updated["recommit_cycles"] > 0,
        "commitment": updated,
    }


def recommit(commitment_id, new_target_date):
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"recommitted": False, "error": "commitment not found"}

    new_cycles = row["recommit_cycles"] + 1
    new_status = "active"
    if new_cycles >= MAX_RECOMMIT_CYCLES:
        new_status = "stopped_asking"

    cur.execute(
        """
        UPDATE commitments
        SET slip_count = 0, recommit_cycles = ?, current_target_date = ?, status = ?
        WHERE id = ?
        """,
        (new_cycles, new_target_date, new_status, commitment_id),
    )
    conn.commit()
    conn.close()
    return {
        "recommitted": True,
        "id": commitment_id,
        "recommit_cycles": new_cycles,
        "status": new_status,
    }


def complete_commitment(commitment_id):
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE commitments SET status = 'completed' WHERE id = ?",
        (commitment_id,),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"completed": updated > 0, "id": commitment_id}


def archive_commitment(commitment_id, reason):
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE commitments SET status = 'archived', archived_reason = ? WHERE id = ?",
        (reason, commitment_id),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return {"archived": updated > 0, "id": commitment_id, "reason": reason}


def list_commitments(status):
    conn = init_db()
    cur = conn.cursor()
    if status == "all":
        cur.execute("SELECT * FROM commitments ORDER BY created_at DESC")
    else:
        cur.execute("SELECT * FROM commitments WHERE status = ? ORDER BY created_at DESC", (status,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"status": status, "count": len(rows), "commitments": rows}


def main():
    parser = argparse.ArgumentParser(description="Honest Re-Commitment — slip-aware commitment tracking")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cap = sub.add_parser("capture")
    p_cap.add_argument("--title", required=True)
    p_cap.add_argument("--original-text", required=True)
    p_cap.add_argument("--target-date", required=True)

    p_find = sub.add_parser("find")
    p_find.add_argument("--query", required=True)

    p_slip = sub.add_parser("slip")
    p_slip.add_argument("--id", type=int, required=True)
    p_slip.add_argument("--new-target-date", default=None)
    p_slip.add_argument("--reason", default="")

    p_re = sub.add_parser("recommit")
    p_re.add_argument("--id", type=int, required=True)
    p_re.add_argument("--new-target-date", required=True)

    p_done = sub.add_parser("complete")
    p_done.add_argument("--id", type=int, required=True)

    p_arch = sub.add_parser("archive")
    p_arch.add_argument("--id", type=int, required=True)
    p_arch.add_argument("--reason", default="user let it go")

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default="active",
                        choices=["active", "completed", "archived", "stopped_asking", "all"])

    args = parser.parse_args()

    if args.command == "capture":
        result = capture_commitment(args.title, args.original_text, args.target_date)
    elif args.command == "find":
        result = find_commitments(args.query)
    elif args.command == "slip":
        result = slip_commitment(args.id, args.new_target_date, args.reason)
    elif args.command == "recommit":
        result = recommit(args.id, args.new_target_date)
    elif args.command == "complete":
        result = complete_commitment(args.id)
    elif args.command == "archive":
        result = archive_commitment(args.id, args.reason)
    elif args.command == "list":
        result = list_commitments(args.status)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
