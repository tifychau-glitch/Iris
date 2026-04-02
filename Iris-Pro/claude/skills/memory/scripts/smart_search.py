#!/usr/bin/env python3
"""
Script: Smart Memory Search
Purpose: Enhanced retrieval with temporal decay, MMR diversity, and hybrid BM25+vector search.
         Drop-in upgrade over mem0_search.py — same interface, better results.

Usage:
    python .claude/skills/memory/scripts/smart_search.py --query "image generation preferences"
    python .claude/skills/memory/scripts/smart_search.py --query "API limits" --limit 5
    python .claude/skills/memory/scripts/smart_search.py --query "gpt-4.1-nano" --vector-weight 0.3 --text-weight 0.7
    python .claude/skills/memory/scripts/smart_search.py --rebuild-index
"""

import argparse
import json
import math
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mem0_client import HISTORY_DB_PATH

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_HALF_LIFE_DAYS = 30
DEFAULT_MMR_LAMBDA = 0.7
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_TEXT_WEIGHT = 0.3
FTS_TABLE = "memory_fts"


# ---------------------------------------------------------------------------
# FTS5 index management
# ---------------------------------------------------------------------------

def _get_fts_conn():
    conn = sqlite3.connect(str(HISTORY_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_fts_table(conn):
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE}
        USING fts5(memory_id, memory)
    """)
    conn.commit()


def rebuild_fts_index():
    """Populate FTS5 from the current state of the history table. Idempotent."""
    conn = _get_fts_conn()
    ensure_fts_table(conn)
    conn.execute(f"DELETE FROM {FTS_TABLE}")

    rows = conn.execute("""
        SELECT h.memory_id, h.new_memory AS memory
        FROM history h
        INNER JOIN (
            SELECT memory_id, MAX(rowid) AS max_rowid
            FROM history WHERE is_deleted = 0
            GROUP BY memory_id
        ) latest ON h.memory_id = latest.memory_id AND h.rowid = latest.max_rowid
        WHERE h.event != 'DELETE' AND h.new_memory IS NOT NULL
    """).fetchall()

    for row in rows:
        conn.execute(
            f"INSERT INTO {FTS_TABLE}(memory_id, memory) VALUES (?, ?)",
            (row["memory_id"], row["memory"]),
        )

    conn.commit()
    count = len(rows)
    conn.close()
    return {"status": "rebuilt", "indexed": count}


def index_single_memory(memory_id, memory_text):
    """Add or update a single memory in the FTS index. Called after mem0 add."""
    conn = _get_fts_conn()
    ensure_fts_table(conn)
    conn.execute(f"DELETE FROM {FTS_TABLE} WHERE memory_id = ?", (memory_id,))
    conn.execute(
        f"INSERT INTO {FTS_TABLE}(memory_id, memory) VALUES (?, ?)",
        (memory_id, memory_text),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# BM25 keyword search
# ---------------------------------------------------------------------------

def bm25_search(query, limit=20):
    """BM25-ranked keyword search via FTS5."""
    conn = _get_fts_conn()
    ensure_fts_table(conn)

    sql = f"""
        SELECT memory_id, memory, bm25({FTS_TABLE}) AS score
        FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH ? ORDER BY score LIMIT ?
    """

    try:
        rows = conn.execute(sql, (query, limit)).fetchall()
    except Exception:
        escaped = '"' + query.replace('"', '""') + '"'
        try:
            rows = conn.execute(sql, (escaped, limit)).fetchall()
        except Exception:
            conn.close()
            return []

    conn.close()
    return [
        {"memory_id": r["memory_id"], "memory": r["memory"], "bm25_score": -r["score"]}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Temporal decay
# ---------------------------------------------------------------------------

def apply_temporal_decay(results, half_life_days=DEFAULT_HALF_LIFE_DAYS):
    """Apply exponential decay based on memory age. Modifies results in-place."""
    decay_lambda = math.log(2) / half_life_days
    now = datetime.now(timezone.utc)

    for item in results:
        ts_str = item.get("updated_at") or item.get("created_at") or ""
        try:
            ts = ts_str if isinstance(ts_str, datetime) else datetime.fromisoformat(str(ts_str))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (now - ts).total_seconds() / 86400
        except (ValueError, TypeError):
            age_days = 0

        base_score = item.get("score", item.get("fused_score", 0.5))
        item["age_days"] = round(age_days, 1)
        item["decayed_score"] = base_score * math.exp(-decay_lambda * age_days)

    return results


# ---------------------------------------------------------------------------
# MMR re-ranking
# ---------------------------------------------------------------------------

def _tokenize(text):
    return set(re.findall(r"\w+", text.lower()))


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def apply_mmr(results, limit, mmr_lambda=DEFAULT_MMR_LAMBDA):
    """Maximal Marginal Relevance — diverse re-ranking via Jaccard similarity."""
    if not results or limit <= 0:
        return results[:limit]

    for item in results:
        item["_tokens"] = _tokenize(item.get("memory", ""))

    candidates = sorted(results, key=lambda x: x.get("decayed_score", 0), reverse=True)
    selected = [candidates.pop(0)]

    while len(selected) < limit and candidates:
        best_score = -float("inf")
        best_idx = 0
        for i, cand in enumerate(candidates):
            relevance = cand.get("decayed_score", 0)
            max_sim = max(_jaccard(cand["_tokens"], s["_tokens"]) for s in selected)
            mmr = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim
            if mmr > best_score:
                best_score = mmr
                best_idx = i
        selected.append(candidates.pop(best_idx))

    for item in selected:
        item.pop("_tokens", None)
    return selected


# ---------------------------------------------------------------------------
# Score utilities
# ---------------------------------------------------------------------------

def _normalize(items, key):
    scores = [item.get(key, 0) for item in items]
    if not scores:
        return
    lo, hi = min(scores), max(scores)
    spread = hi - lo if hi > lo else 1.0
    for item in items:
        item[key] = (item.get(key, 0) - lo) / spread


def _get_timestamp(memory_id):
    try:
        conn = _get_fts_conn()
        row = conn.execute(
            "SELECT created_at FROM history WHERE memory_id = ? ORDER BY rowid DESC LIMIT 1",
            (memory_id,),
        ).fetchone()
        conn.close()
        return row["created_at"] if row else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def smart_search(query, limit=10, vector_weight=DEFAULT_VECTOR_WEIGHT,
                 text_weight=DEFAULT_TEXT_WEIGHT, half_life_days=DEFAULT_HALF_LIFE_DAYS,
                 mmr_lambda=DEFAULT_MMR_LAMBDA):
    """Enhanced memory search: vector + BM25 fusion, temporal decay, MMR diversity.

    Returns same format as mem0_search: {"results": [{"id", "memory", "score", ...}]}
    """
    fetch_limit = max(limit * 3, 15)

    # --- Vector search via mem0 ---
    from mem0_search import search_memory
    vector_raw = search_memory(query, limit=fetch_limit)
    raw_results = vector_raw.get("results", []) if isinstance(vector_raw, dict) else vector_raw

    items = []
    for r in raw_results:
        items.append({
            "id": r.get("id", ""),
            "memory": r.get("memory", ""),
            "vector_score": r.get("score", 0),
            "created_at": r.get("created_at", ""),
            "updated_at": r.get("updated_at", ""),
        })

    # --- BM25 search ---
    bm25_results = bm25_search(query, limit=fetch_limit)
    bm25_lookup = {r["memory_id"]: r["bm25_score"] for r in bm25_results}

    # Add BM25-only hits (keywords matched but vector missed)
    vec_ids = {item["id"] for item in items}
    for br in bm25_results:
        if br["memory_id"] not in vec_ids:
            items.append({
                "id": br["memory_id"],
                "memory": br["memory"],
                "vector_score": 0,
                "created_at": _get_timestamp(br["memory_id"]),
                "updated_at": "",
            })

    if not items:
        return {"results": []}

    # --- Normalize vector scores to [0, 1] ---
    _normalize(items, "vector_score")

    # --- Attach normalized BM25 scores ---
    max_bm25 = max(bm25_lookup.values()) if bm25_lookup else 1.0
    for item in items:
        raw = bm25_lookup.get(item["id"], 0)
        item["bm25_score"] = raw / max_bm25 if max_bm25 > 0 else 0

    # --- Fuse ---
    for item in items:
        item["fused_score"] = vector_weight * item["vector_score"] + text_weight * item["bm25_score"]
        item["score"] = item["fused_score"]

    # --- Temporal decay ---
    apply_temporal_decay(items, half_life_days)
    for item in items:
        item["score"] = item["decayed_score"]

    # --- MMR re-rank ---
    final = apply_mmr(items, limit, mmr_lambda)

    # --- Format output ---
    output = []
    for item in final:
        output.append({
            "id": item["id"],
            "memory": item["memory"],
            "score": round(item.get("decayed_score", item.get("score", 0)), 4),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
            "debug": {
                "vector": round(item.get("vector_score", 0), 4),
                "bm25": round(item.get("bm25_score", 0), 4),
                "fused": round(item.get("fused_score", 0), 4),
                "age_days": item.get("age_days", 0),
                "decayed": round(item.get("decayed_score", 0), 4),
            },
        })

    return {"results": output}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Smart memory search — temporal decay, MMR diversity, hybrid BM25+vector"
    )
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--vector-weight", type=float, default=DEFAULT_VECTOR_WEIGHT)
    parser.add_argument("--text-weight", type=float, default=DEFAULT_TEXT_WEIGHT)
    parser.add_argument("--half-life", type=float, default=DEFAULT_HALF_LIFE_DAYS)
    parser.add_argument("--mmr-lambda", type=float, default=DEFAULT_MMR_LAMBDA)
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild FTS5 index from history DB")
    args = parser.parse_args()

    if args.rebuild_index:
        result = rebuild_fts_index()
        print(json.dumps(result, indent=2))
        return

    if not args.query:
        parser.error("--query is required (unless using --rebuild-index)")

    results = smart_search(
        query=args.query, limit=args.limit,
        vector_weight=args.vector_weight, text_weight=args.text_weight,
        half_life_days=args.half_life, mmr_lambda=args.mmr_lambda,
    )
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
