"""
Constraint Diagnoser — Identifies the real bottleneck from accountability data.

Reads excuse categories, time-of-day patterns, and avoidance patterns to
classify the user's primary constraint. Returns structured JSON for
Iris to interpret conversationally.

Usage: python3 diagnose.py [--min-days 7]
"""

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "iris_accountability.db"


def get_connection():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def diagnose(min_days=7):
    conn = get_connection()
    if not conn:
        return {"error": "No accountability database found", "available": False}

    # Check data volume
    day_count = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_scores"
    ).fetchone()[0]

    if day_count < min_days:
        conn.close()
        return {
            "available": False,
            "days_tracked": day_count,
            "min_days": min_days,
            "message": f"Need {min_days} days of data. Currently have {day_count}.",
        }

    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # --- Gather signals ---

    # 1. Excuse category distribution
    excuse_rows = conn.execute(
        """SELECT excuse_category, COUNT(*) as cnt FROM commitments
           WHERE excuse_category IS NOT NULL AND due_date >= ?
           GROUP BY excuse_category ORDER BY cnt DESC""",
        (cutoff,)
    ).fetchall()
    excuse_counts = {r["excuse_category"]: r["cnt"] for r in excuse_rows}
    total_excuses = sum(excuse_counts.values()) or 1

    # 2. Commitment volume vs completion
    total_made = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ?", (cutoff,)
    ).fetchone()[0]
    total_completed = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE due_date >= ? AND completed = 1", (cutoff,)
    ).fetchone()[0]
    total_open = conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE completed = 0 AND skipped = 0 AND due_date >= ?", (cutoff,)
    ).fetchone()[0]

    # 3. Most avoided categories
    avoided_rows = conn.execute(
        """SELECT category, COUNT(*) as cnt FROM commitments
           WHERE (skipped = 1 OR (completed = 0 AND due_date < date('now')))
           AND due_date >= ?
           GROUP BY category ORDER BY cnt DESC LIMIT 3""",
        (cutoff,)
    ).fetchall()
    avoided_cats = {r["category"]: r["cnt"] for r in avoided_rows}

    # 4. Average commitments per day
    avg_per_day = total_made / max(day_count, 1)

    # 5. Completion rate
    completion_rate = total_completed / max(total_made, 1)

    conn.close()

    # --- Classify constraint ---

    constraints = []

    # Clarity: high 'unclear_task' excuse rate
    unclear_pct = excuse_counts.get("unclear_task", 0) / total_excuses
    if unclear_pct >= 0.3:
        constraints.append({
            "type": "clarity",
            "score": unclear_pct,
            "evidence": f"{int(unclear_pct * 100)}% of missed commitments were tagged as unclear tasks",
            "suggestion": "Before committing, define what 'done' looks like in one sentence. If you can't, the task is too vague.",
        })

    # Avoidance: high 'avoidance' excuse rate + repeating categories
    avoidance_pct = excuse_counts.get("avoidance", 0) / total_excuses
    if avoidance_pct >= 0.25:
        top_avoided = list(avoided_cats.keys())[:2]
        constraints.append({
            "type": "avoidance",
            "score": avoidance_pct,
            "evidence": f"{int(avoidance_pct * 100)}% of misses are avoidance. Most avoided: {', '.join(top_avoided)}",
            "suggestion": "The task you keep avoiding is the one that matters most. Start with 10 minutes on it — just 10.",
        })

    # Calendar/overcommitment: high volume + low completion
    if avg_per_day > 4 and completion_rate < 0.5:
        constraints.append({
            "type": "calendar",
            "score": avg_per_day / 10,
            "evidence": f"Averaging {avg_per_day:.1f} commitments/day but only completing {int(completion_rate * 100)}%",
            "suggestion": "Cut your daily commitments in half. Three things done beats six things planned.",
        })

    # Decision overload: many open commitments
    if total_open > 8:
        constraints.append({
            "type": "decision_overload",
            "score": total_open / 20,
            "evidence": f"{total_open} commitments currently open and unresolved",
            "suggestion": "Close or skip the stale ones. Open loops drain energy even when you're not looking at them.",
        })

    # Energy: high 'energy' excuse rate
    energy_pct = excuse_counts.get("energy", 0) / total_excuses
    if energy_pct >= 0.25:
        constraints.append({
            "type": "energy",
            "score": energy_pct,
            "evidence": f"{int(energy_pct * 100)}% of misses cite energy as the reason",
            "suggestion": "Move your hardest commitment to your first 2 hours. Don't save it for when you're depleted.",
        })

    # Sizing: lots of tasks across categories, low completion everywhere
    if len(avoided_cats) >= 3 and completion_rate < 0.5 and avg_per_day > 2:
        constraints.append({
            "type": "sizing",
            "score": 0.6,
            "evidence": f"Missing tasks across {len(avoided_cats)}+ categories — not one area, everything",
            "suggestion": "Your tasks might be too big. Break each one into a 15-minute first step.",
        })

    # Forgot: high 'forgot' rate
    forgot_pct = excuse_counts.get("forgot", 0) / total_excuses
    if forgot_pct >= 0.25:
        constraints.append({
            "type": "system",
            "score": forgot_pct,
            "evidence": f"{int(forgot_pct * 100)}% of misses are simply forgotten",
            "suggestion": "This isn't a discipline problem — it's a reminder problem. Set due times so I can follow up.",
        })

    # Sort by score
    constraints.sort(key=lambda c: c["score"], reverse=True)

    if not constraints:
        return {
            "available": True,
            "primary_constraint": None,
            "message": "No clear pattern detected. Completion rate is reasonable or data is spread evenly.",
            "completion_rate": round(completion_rate, 2),
            "days_tracked": day_count,
        }

    primary = constraints[0]
    return {
        "available": True,
        "primary_constraint": primary["type"],
        "confidence": "high" if primary["score"] >= 0.4 else "medium" if primary["score"] >= 0.25 else "low",
        "evidence": primary["evidence"],
        "suggestion": primary["suggestion"],
        "all_constraints": constraints,
        "completion_rate": round(completion_rate, 2),
        "days_tracked": day_count,
        "avg_commitments_per_day": round(avg_per_day, 1),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Constraint Diagnoser")
    parser.add_argument("--min-days", type=int, default=7)
    args = parser.parse_args()

    result = diagnose(min_days=args.min_days)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
