"""
Tool: IRIS Journal
Purpose: Unified, read-only view of everything IRIS has silently captured
         across her skills. Reads from individual skill databases, computes
         current state at read time, and presents a chronological feed.
Usage: python3 scripts/journal.py <command> [options]

Commands:
  read     Show journal entries (with optional --days, --source, --format)
  summary  High-level snapshot of current state across all sources

Sources currently wired:
  - friction-log      (reads from data/friction_log.db)
  - goal-decay-tracker (reads from data/goals.db)

To add a new source: implement a reader function and add it to SOURCES.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
FRICTION_DB = DATA_DIR / "friction_log.db"
GOALS_DB = DATA_DIR / "goals.db"
COMMITMENTS_DB = DATA_DIR / "commitments.db"
ENERGY_DB = DATA_DIR / "energy_events.db"

FRICTION_SURFACE_THRESHOLD = 3
FRICTION_PATTERN_WINDOW_DAYS = 30
FRICTION_QUIET_DAYS = 14

GOAL_DECAY_WINDOWS = {"short": 7, "medium": 21, "long": 45}

COMMITMENT_SLIP_THRESHOLD = 3
COMMITMENT_MAX_RECOMMIT_CYCLES = 2

ENERGY_MIN_EVENTS_FOR_INSIGHT = 15


def _open(db_path):
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def read_friction(days):
    conn = _open(FRICTION_DB)
    if conn is None:
        return []

    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT * FROM friction_log WHERE timestamp >= ? ORDER BY timestamp DESC",
        (cutoff,),
    )
    rows = cur.fetchall()

    # Load surfaced patterns for state computation
    cur.execute("SELECT * FROM surfaced_patterns")
    surfaced = {r["category"]: dict(r) for r in cur.fetchall()}

    # For each category, compute current count in the 30-day window
    cur.execute(
        """
        SELECT category, COUNT(*) as count, MAX(timestamp) as latest
        FROM friction_log
        WHERE timestamp >= ?
        GROUP BY category
        """,
        ((datetime.now() - timedelta(days=FRICTION_PATTERN_WINDOW_DAYS)).isoformat(),),
    )
    category_stats = {r["category"]: dict(r) for r in cur.fetchall()}

    conn.close()

    entries = []
    now = datetime.now()
    for r in rows:
        cat = r["category"]
        stats = category_stats.get(cat, {"count": 0, "latest": None})
        count = stats["count"]
        latest = stats["latest"]

        is_surfaced = cat in surfaced
        days_since_latest = None
        if latest:
            days_since_latest = (now - datetime.fromisoformat(latest)).days

        # Compute state and note
        if is_surfaced:
            state = "surfaced"
            note = f"Pattern mentioned already. Won't bring it up again unless it goes quiet and comes back."
        elif count >= FRICTION_SURFACE_THRESHOLD:
            state = "ready to surface"
            note = f"Threshold hit ({count} in {FRICTION_PATTERN_WINDOW_DAYS} days). Will weave into next relevant conversation."
        elif days_since_latest is not None and days_since_latest >= FRICTION_QUIET_DAYS:
            state = "quiet"
            note = f"Logged but hasn't recurred in {days_since_latest} days. Not a pattern right now."
        else:
            remaining = FRICTION_SURFACE_THRESHOLD - count
            state = f"watching ({count}/{FRICTION_SURFACE_THRESHOLD} before surfacing)"
            if remaining == 1:
                note = "One more and I'll bring it up."
            elif remaining == 2:
                note = "Logging quietly. Need one more to see if it's a real pattern."
            else:
                note = "Just logged. No pattern yet."

        entries.append({
            "timestamp": r["timestamp"],
            "source": "friction-log",
            "type": cat,
            "what": r["friction_text"],
            "thing": r["thing"] or None,
            "state": state,
            "note": note,
            "id": r["id"],
        })

    return entries


def read_goals(days):
    conn = _open(GOALS_DB)
    if conn is None:
        return []

    cur = conn.cursor()
    # For goals, "timestamp" for journal purposes is created_at.
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT * FROM goals WHERE created_at >= ? OR last_touched >= ? OR (last_surfaced_at IS NOT NULL AND last_surfaced_at >= ?) ORDER BY created_at DESC",
        (cutoff, cutoff, cutoff),
    )
    rows = cur.fetchall()
    conn.close()

    entries = []
    now = datetime.now()
    for r in rows:
        timeframe = r["timeframe"]
        decay_days = GOAL_DECAY_WINDOWS.get(timeframe, 21)
        last_touched = datetime.fromisoformat(r["last_touched"])
        days_quiet = (now - last_touched).days
        days_until_stale = decay_days - days_quiet

        if r["status"] == "archived":
            state = "archived"
            note = f"Archived: {r['archived_reason'] or 'no reason given'}."
        elif r["surfaced_count"] >= 3:
            state = "stopped surfacing"
            note = "Surfaced 3 times without real movement. Won't bring it up again unless you do."
        elif r["last_surfaced_at"] and days_quiet < decay_days:
            state = "surfaced (active)"
            note = "Mentioned recently; user said still alive. Watching again."
        elif days_quiet >= decay_days:
            state = f"stale ({days_quiet} days quiet)"
            note = f"Past the {decay_days}-day decay window. Ready to surface softly."
        elif days_until_stale <= 3:
            state = f"approaching decay ({days_until_stale} days until stale)"
            note = "Hasn't come up in a while. Will check in soon if it stays quiet."
        else:
            state = "active"
            note = f"Fresh. Will check in if quiet for {decay_days} days."

        entries.append({
            "timestamp": r["created_at"],
            "source": "goal-decay-tracker",
            "type": f"goal ({timeframe})",
            "what": r["original_text"],
            "thing": r["title"],
            "state": state,
            "note": note,
            "id": r["id"],
        })

    return entries


def read_commitments(days):
    conn = _open(COMMITMENTS_DB)
    if conn is None:
        return []

    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        """
        SELECT * FROM commitments
        WHERE created_at >= ?
           OR (last_slip_at IS NOT NULL AND last_slip_at >= ?)
           OR (last_surfaced_at IS NOT NULL AND last_surfaced_at >= ?)
        ORDER BY created_at DESC
        """,
        (cutoff, cutoff, cutoff),
    )
    rows = cur.fetchall()
    conn.close()

    entries = []
    for r in rows:
        slip_count = r["slip_count"]
        cycles = r["recommit_cycles"]
        status = r["status"]

        if status == "completed":
            state = "completed"
            note = "Done. Counter cleared."
        elif status == "archived":
            state = "archived"
            note = f"Archived: {r['archived_reason'] or 'no reason given'}."
        elif status == "stopped_asking":
            state = "stopped asking"
            note = "Asked twice already. Won't bring it up again unless you do."
        elif slip_count >= COMMITMENT_SLIP_THRESHOLD:
            label = "ready to ask again" if cycles > 0 else "ready to ask"
            state = label
            if cycles > 0:
                note = "Slipped past threshold a second time. Will ask once more, gently."
            else:
                note = "Slipped 3 times. Will ask 'still a yes?' in next natural opening."
        elif slip_count > 0:
            remaining = COMMITMENT_SLIP_THRESHOLD - slip_count
            state = f"watching ({slip_count}/{COMMITMENT_SLIP_THRESHOLD} slips)"
            if remaining == 1:
                note = "One more slip and I'll ask if it's still a yes."
            else:
                note = "Logged the slip. Watching for a pattern."
        else:
            state = "active"
            note = f"On track. Target: {r['current_target_date']}."

        entries.append({
            "timestamp": r["last_slip_at"] or r["created_at"],
            "source": "honest-recommit",
            "type": f"commitment ({status})",
            "what": r["original_text"],
            "thing": r["title"],
            "state": state,
            "note": note,
            "id": r["id"],
        })

    return entries


def read_energy(days):
    conn = _open(ENERGY_DB)
    if conn is None:
        return []

    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT * FROM energy_events WHERE timestamp >= ? ORDER BY timestamp DESC",
        (cutoff,),
    )
    rows = cur.fetchall()

    cur.execute("SELECT COUNT(*) as c FROM energy_events")
    total = cur.fetchone()["c"]

    cur.execute("SELECT * FROM surfaced_insights ORDER BY surfaced_at DESC LIMIT 5")
    insights = [dict(r) for r in cur.fetchall()]
    conn.close()

    entries = []
    remaining_to_threshold = max(0, ENERGY_MIN_EVENTS_FOR_INSIGHT - total)

    for r in rows:
        if total < ENERGY_MIN_EVENTS_FOR_INSIGHT:
            state = f"collecting ({total}/{ENERGY_MIN_EVENTS_FOR_INSIGHT} events)"
            note = f"Need {remaining_to_threshold} more events before patterns are meaningful."
        else:
            state = "ready for insights"
            if insights:
                latest = insights[0]
                note = f"Latest insight surfaced: {latest['description']}"
            else:
                note = "Threshold reached. Insights will surface when a clear pattern exists."

        entries.append({
            "timestamp": r["timestamp"],
            "source": "energy-mapping",
            "type": f"shipped ({r['category']})",
            "what": r["what"],
            "thing": None,
            "state": state,
            "note": note,
            "id": r["id"],
        })

    return entries


SOURCES = {
    "friction-log": read_friction,
    "goal-decay-tracker": read_goals,
    "honest-recommit": read_commitments,
    "energy-mapping": read_energy,
}


def read_journal(days, source_filter=None):
    all_entries = []
    if source_filter:
        if source_filter not in SOURCES:
            return {"error": f"unknown source: {source_filter}", "valid": list(SOURCES.keys())}
        all_entries = SOURCES[source_filter](days)
    else:
        for name, reader in SOURCES.items():
            all_entries.extend(reader(days))

    all_entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return {"days": days, "source": source_filter or "all", "count": len(all_entries), "entries": all_entries}


def summary():
    result = {
        "friction_log": {"available": FRICTION_DB.exists()},
        "goal_decay": {"available": GOALS_DB.exists()},
        "honest_recommit": {"available": COMMITMENTS_DB.exists()},
        "energy_mapping": {"available": ENERGY_DB.exists()},
    }

    if FRICTION_DB.exists():
        conn = _open(FRICTION_DB)
        cur = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=FRICTION_PATTERN_WINDOW_DAYS)).isoformat()
        cur.execute("SELECT COUNT(*) as c FROM friction_log WHERE timestamp >= ?", (cutoff,))
        total = cur.fetchone()["c"]
        cur.execute(
            """
            SELECT category, COUNT(*) as count
            FROM friction_log WHERE timestamp >= ?
            GROUP BY category
            """,
            (cutoff,),
        )
        by_cat = {r["category"]: r["count"] for r in cur.fetchall()}
        watching = {k: v for k, v in by_cat.items() if v < FRICTION_SURFACE_THRESHOLD}
        ready = {k: v for k, v in by_cat.items() if v >= FRICTION_SURFACE_THRESHOLD}
        cur.execute("SELECT COUNT(*) as c FROM surfaced_patterns")
        surfaced_count = cur.fetchone()["c"]
        conn.close()

        result["friction_log"].update({
            "total_in_window": total,
            "watching": watching,
            "at_or_above_threshold": ready,
            "already_surfaced_patterns": surfaced_count,
        })

    if GOALS_DB.exists():
        conn = _open(GOALS_DB)
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) as c FROM goals GROUP BY status")
        by_status = {r["status"]: r["c"] for r in cur.fetchall()}
        cur.execute("SELECT * FROM goals WHERE status = 'active'")
        active = cur.fetchall()
        conn.close()

        now = datetime.now()
        stale = 0
        approaching = 0
        fresh = 0
        for g in active:
            decay_days = GOAL_DECAY_WINDOWS.get(g["timeframe"], 21)
            days_quiet = (now - datetime.fromisoformat(g["last_touched"])).days
            if days_quiet >= decay_days:
                stale += 1
            elif decay_days - days_quiet <= 3:
                approaching += 1
            else:
                fresh += 1

        result["goal_decay"].update({
            "active": by_status.get("active", 0),
            "archived": by_status.get("archived", 0),
            "fresh": fresh,
            "approaching_decay": approaching,
            "stale": stale,
        })

    if COMMITMENTS_DB.exists():
        conn = _open(COMMITMENTS_DB)
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) as c FROM commitments GROUP BY status")
        by_status = {r["status"]: r["c"] for r in cur.fetchall()}
        cur.execute(
            "SELECT COUNT(*) as c FROM commitments WHERE slip_count >= ? AND status = 'active'",
            (COMMITMENT_SLIP_THRESHOLD,),
        )
        ready_to_ask = cur.fetchone()["c"]
        cur.execute(
            "SELECT COUNT(*) as c FROM commitments WHERE slip_count > 0 AND slip_count < ? AND status = 'active'",
            (COMMITMENT_SLIP_THRESHOLD,),
        )
        watching = cur.fetchone()["c"]
        conn.close()

        result["honest_recommit"].update({
            "active": by_status.get("active", 0),
            "completed": by_status.get("completed", 0),
            "archived": by_status.get("archived", 0),
            "stopped_asking": by_status.get("stopped_asking", 0),
            "watching_slips": watching,
            "ready_to_ask": ready_to_ask,
        })

    if ENERGY_DB.exists():
        conn = _open(ENERGY_DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM energy_events")
        total = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM surfaced_insights")
        surfaced = cur.fetchone()["c"]
        conn.close()

        result["energy_mapping"].update({
            "total_events": total,
            "ready_for_insights": total >= ENERGY_MIN_EVENTS_FOR_INSIGHT,
            "events_until_threshold": max(0, ENERGY_MIN_EVENTS_FOR_INSIGHT - total),
            "insights_surfaced": surfaced,
        })

    return result


def format_text(journal_data):
    if "error" in journal_data:
        return f"error: {journal_data['error']}"

    lines = []
    lines.append(f"IRIS Journal — last {journal_data['days']} days ({journal_data['count']} entries)")
    lines.append("=" * 60)
    lines.append("")

    if journal_data["count"] == 0:
        lines.append("(nothing captured yet)")
        return "\n".join(lines)

    for e in journal_data["entries"]:
        ts = e["timestamp"][:16].replace("T", "  ")
        lines.append(f"{ts}   {e['source']:<22} {e['type']}")
        if e.get("thing"):
            lines.append(f"           \"{e['what']}\"  [{e['thing']}]")
        else:
            lines.append(f"           \"{e['what']}\"")
        lines.append(f"           state: {e['state']}")
        lines.append(f"           note:  {e['note']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="IRIS Journal — read silent-capture observations")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="Read journal entries")
    p_read.add_argument("--days", type=int, default=7)
    p_read.add_argument("--source", choices=list(SOURCES.keys()), default=None)
    p_read.add_argument("--format", choices=["json", "text"], default="json")

    sub.add_parser("summary", help="High-level snapshot")

    args = parser.parse_args()

    if args.command == "read":
        result = read_journal(args.days, args.source)
        if args.format == "text":
            print(format_text(result))
        else:
            print(json.dumps(result, indent=2, default=str))
    elif args.command == "summary":
        print(json.dumps(summary(), indent=2, default=str))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
