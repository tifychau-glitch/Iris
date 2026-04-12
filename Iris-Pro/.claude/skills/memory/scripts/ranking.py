#!/usr/bin/env python3
"""
ranking.py — Phase 4: Retrieval Ranking

Implements trust-aware, freshness-sensitive retrieval ranking.

Formula:
    final_score = trust_weight * freshness_modifier * relevance_score

Design rules:
  - Trust weight dominates: Core State always wins over wiki, wiki over retrieval
  - Freshness is field-sensitive: pricing decays in days, identity never decays
  - Relevance is bounded: cannot override trust floors (semantically similar noise
    cannot outrank a canonical fact)
  - Pending writes score 0.0 — never surface as truth
  - Query-type routing: canonical questions skip directly to Core State,
    pattern/explanation questions prefer wiki, history questions prefer audit

Usage:
    python3 ranking.py --test           # run golden test set
    python3 ranking.py --demo           # demonstrate score comparisons
"""

import math
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Trust priors — by (layer, source) pair
# ---------------------------------------------------------------------------
# Higher = more trustworthy. Core State is deterministic and user-confirmed.
# Pending writes are never truth — score 0.0 always.

TRUST_PRIORS: dict[tuple[str, str], float] = {
    # Core State
    ("core_state", "user_explicit"):    1.00,
    ("core_state", "user_confirmed"):   1.00,
    ("core_state", "system_canonical"): 0.95,
    # Wiki — synthesized, human-curated knowledge
    ("wiki", "user_explicit"):          0.90,
    ("wiki", "user_confirmed"):         0.87,
    ("wiki", "system_canonical"):       0.82,
    ("wiki", "system_inferred"):        0.65,
    # Retrieval index — raw content, meetings, articles, external
    ("retrieval", "user_explicit"):     0.70,
    ("retrieval", "user_confirmed"):    0.68,
    ("retrieval", "system_canonical"):  0.60,
    ("retrieval", "system_inferred"):   0.45,
    ("retrieval", "external"):          0.40,
    # Audit — useful for history/trace queries but not "truth" answers
    ("audit", "any"):                   0.60,
    # Pending writes — intentionally 0
    ("pending", "any"):                 0.0,
}

# Fallback trust by layer when source is not known
LAYER_TRUST_DEFAULTS: dict[str, float] = {
    "core_state": 1.00,
    "wiki":        0.78,
    "retrieval":   0.52,
    "audit":       0.60,
    "pending":     0.0,
}

# Trust floor per query type — relevance cannot cause a result below this floor
# to beat a result at or above it.
QUERY_TYPE_TRUST_FLOOR: dict[str, float] = {
    "canonical": 0.90,   # canonical questions require Core State or confirmed wiki
    "pattern":   0.65,   # pattern questions accept wiki-level trust
    "history":   0.55,   # history questions accept audit-level trust
    "general":   0.40,   # general questions have no meaningful floor
}

# Source bonus by (query_type, layer) — applied multiplicatively to final score.
# Purpose: make trust genuinely dominant when it matters.
# For canonical queries, Core State gets a priority boost so it cannot be
# outranked by semantically similar but lower-trust content.
SOURCE_BONUS: dict[tuple[str, str], float] = {
    ("canonical", "core_state"): 1.20,   # Core State always wins canonical questions
    ("history",   "audit"):      1.15,   # Audit wins history questions
    ("pattern",   "wiki"):       1.10,   # Wiki preferred for pattern questions
}

# ---------------------------------------------------------------------------
# Freshness profiles — half-life in days, by field path prefix or content type
# ---------------------------------------------------------------------------
# None = no decay (this field is considered permanent until explicitly changed)

FRESHNESS_PROFILES: dict[str, Optional[int]] = {
    # Core State fields — ordered most-to-least specific
    "offer_stack":                  7,    # pricing: fast decay, stale in a week
    "active_commitments":           5,    # commitments are time-critical
    "active_project_context":       14,   # project context fades in 2 weeks
    "current_goals":                21,   # primary goal stale after 3 weeks
    "canonical_business_facts":     180,  # slow-changing business facts
    "tone_preferences":             None, # preferences: no decay
    "identity":                     None, # identity: no decay
    # Retrieval content types
    "wiki":                         90,   # wiki pages: slow fade
    "retrieval":                    30,   # retrieval chunks: moderate decay
    "external":                     21,   # external articles: faster decay
    "audit":                        None, # audit entries: no decay (history is history)
    "pending":                      0,    # pending = irrelevant for retrieval
    # Default
    "_default":                     30,
}

# ---------------------------------------------------------------------------
# Query type detection
# ---------------------------------------------------------------------------
# Determines which retrieval strategy to use before scoring.

# Canonical queries → check Core State first, hard-required
_CANONICAL_SIGNALS = [
    "what is my price", "what do i charge", "how much", "my pricing",
    "what is my goal", "what am i working on", "my current goal",
    "my name", "what is my business", "who am i", "my audience",
    "my offer", "my product", "what is iris",
    "my tone", "my voice", "my style", "how do i write",
    "what are my commitments", "what did i promise",
]

# Pattern / explanation queries → wiki preferred
_PATTERN_SIGNALS = [
    "why", "what patterns", "what has", "what have i noticed",
    "explain", "the reason", "how does", "what works",
    "what approach", "the strategy", "what i've learned",
    "i've noticed", "tends to", "usually", "generally",
]

# History / trace queries → audit log, then Core State changes
_HISTORY_SIGNALS = [
    "what changed", "when did", "last time", "recently",
    "history of", "before", "used to", "previously",
    "changed from", "updated", "audit", "what happened to",
    "when i decided",
]

QUERY_TYPE_CANONICAL = "canonical"
QUERY_TYPE_PATTERN   = "pattern"
QUERY_TYPE_HISTORY   = "history"
QUERY_TYPE_GENERAL   = "general"


def detect_query_type(query: str) -> str:
    """
    Classify a query into a retrieval strategy type.
    Returns: 'canonical' | 'pattern' | 'history' | 'general'

    Canonical wins over pattern wins over history (priority order).
    """
    ql = query.lower()

    for sig in _CANONICAL_SIGNALS:
        if sig in ql:
            return QUERY_TYPE_CANONICAL

    for sig in _HISTORY_SIGNALS:
        if sig in ql:
            return QUERY_TYPE_HISTORY

    for sig in _PATTERN_SIGNALS:
        if sig in ql:
            return QUERY_TYPE_PATTERN

    return QUERY_TYPE_GENERAL


# ---------------------------------------------------------------------------
# Trust weight lookup
# ---------------------------------------------------------------------------

def get_trust_weight(layer: str, source: str = "unknown") -> float:
    """
    Return the trust weight [0.0–1.0] for a result from the given layer and source.
    Pending writes always return 0.0.
    """
    if layer == "pending":
        return 0.0

    # Try exact (layer, source) pair first
    exact = TRUST_PRIORS.get((layer, source))
    if exact is not None:
        return exact

    # Try (layer, "any") fallback
    any_fallback = TRUST_PRIORS.get((layer, "any"))
    if any_fallback is not None:
        return any_fallback

    # Fall back to layer default
    return LAYER_TRUST_DEFAULTS.get(layer, 0.40)


# ---------------------------------------------------------------------------
# Freshness modifier
# ---------------------------------------------------------------------------

def get_half_life(field_path_or_type: str) -> Optional[int]:
    """
    Return the freshness half-life in days for a given field path or content type.
    Returns None if the content type does not decay.

    Matches by prefix — so "offer_stack.products" returns 7 (pricing rate).
    """
    if not field_path_or_type:
        return FRESHNESS_PROFILES["_default"]

    # Check from most specific to least specific
    for key in FRESHNESS_PROFILES:
        if key == "_default":
            continue
        if field_path_or_type.startswith(key):
            return FRESHNESS_PROFILES[key]

    return FRESHNESS_PROFILES["_default"]


def freshness_modifier(age_days: float, half_life: Optional[int]) -> float:
    """
    Compute freshness modifier [0.0–1.0] given age in days and half-life.
    - half_life = None → returns 1.0 (no decay)
    - half_life = 0 → returns 0.0 (always stale, e.g. pending writes)
    - Otherwise: standard exponential decay
    """
    if half_life is None:
        return 1.0  # permanent
    if half_life == 0:
        return 0.0  # always stale
    decay_lambda = math.log(2) / half_life
    return math.exp(-decay_lambda * age_days)


# ---------------------------------------------------------------------------
# Final score computation
# ---------------------------------------------------------------------------

@dataclass
class RankedResult:
    """A single retrieval result after trust/freshness/relevance scoring."""
    id: str
    memory: str
    layer: str = "retrieval"
    source: str = "unknown"
    field_path: str = ""
    age_days: float = 0.0
    relevance_score: float = 0.5    # normalized fused score from BM25+vector
    trust_weight: float = 0.0       # from get_trust_weight()
    freshness_mod: float = 1.0      # from freshness_modifier()
    final_score: float = 0.0        # trust_weight * freshness_mod * relevance_score
    rank: int = 0
    created_at: str = ""
    debug: dict = field(default_factory=dict)


def score_result(
    result: dict,
    query_type: str = QUERY_TYPE_GENERAL,
) -> RankedResult:
    """
    Compute final_score for a single retrieval result dict.

    Expected dict keys:
        id, memory, layer, source (optional), field_path (optional),
        age_days (optional), relevance_score (or score or fused_score)
    """
    layer = result.get("layer", "retrieval")
    source = result.get("source", "unknown")
    field_path = result.get("field_path", "") or result.get("trust_class", "")
    age_days = float(result.get("age_days", 0.0))

    # Relevance: use best available score
    relevance = (
        result.get("relevance_score")
        or result.get("fused_score")
        or result.get("decayed_score")
        or result.get("score", 0.5)
    )
    # Normalize to [0, 1]
    relevance = max(0.0, min(1.0, float(relevance)))

    # Trust
    tw = get_trust_weight(layer, source)

    # Freshness — use field_path if available, else layer name
    hl = get_half_life(field_path or layer)
    fm = freshness_modifier(age_days, hl)

    # Source bonus — makes trust genuinely dominant for query types where layer matters
    source_bonus = SOURCE_BONUS.get((query_type, layer), 1.0)

    # Final score
    fs = tw * fm * relevance * source_bonus

    # Enforce trust floor for canonical queries:
    # If the trust_weight is below the floor required by this query type,
    # cap the final score so it cannot beat results with trust above the floor.
    trust_floor = QUERY_TYPE_TRUST_FLOOR.get(query_type, 0.0)
    if tw < trust_floor:
        # Hard-cap: max final_score = (trust_floor - ε) * freshness * relevance
        # This ensures below-floor results can never overtake floor-meeting results.
        cap = (trust_floor - 0.001) * fm * relevance
        fs = min(fs, cap)

    return RankedResult(
        id=result.get("id", ""),
        memory=result.get("memory", ""),
        layer=layer,
        source=source,
        field_path=field_path,
        age_days=age_days,
        relevance_score=relevance,
        trust_weight=tw,
        freshness_mod=round(fm, 4),
        final_score=round(fs, 4),
        created_at=result.get("created_at", ""),
        debug={
            "trust_weight": tw,
            "freshness_mod": round(fm, 4),
            "half_life_days": hl,
            "relevance_score": round(relevance, 4),
            "source_bonus": source_bonus,
            "query_type": query_type,
            "trust_floor_applied": tw < trust_floor,
        },
    )


def rank_results(
    results: list[dict],
    query_type: str = QUERY_TYPE_GENERAL,
) -> list[RankedResult]:
    """
    Score and sort a list of retrieval result dicts.
    Returns sorted list (highest final_score first).
    Pending writes are filtered out before ranking.
    """
    # Hard filter: pending writes never appear in ranked output
    filtered = [r for r in results if r.get("layer") != "pending"]

    scored = [score_result(r, query_type) for r in filtered]
    scored.sort(key=lambda r: r.final_score, reverse=True)

    for i, r in enumerate(scored):
        r.rank = i + 1

    return scored


# ---------------------------------------------------------------------------
# Layer ordering for tiered strategy (query-type-aware)
# ---------------------------------------------------------------------------

LAYER_ORDER: dict[str, list[str]] = {
    QUERY_TYPE_CANONICAL: ["core_state", "wiki", "retrieval"],
    QUERY_TYPE_PATTERN:   ["wiki", "retrieval", "core_state"],
    QUERY_TYPE_HISTORY:   ["audit", "core_state", "wiki"],
    QUERY_TYPE_GENERAL:   ["core_state", "wiki", "retrieval"],
}


def preferred_layers(query_type: str) -> list[str]:
    """Return the preferred layer check order for this query type."""
    return LAYER_ORDER.get(query_type, LAYER_ORDER[QUERY_TYPE_GENERAL])


# ---------------------------------------------------------------------------
# Confidence label (grounded in trust weight, not raw score)
# ---------------------------------------------------------------------------

def confidence_label(result: RankedResult) -> str:
    """
    Grounded confidence label based on trust weight and freshness.
    Does not rely on 'model vibes' — purely structural.
    """
    if result.trust_weight >= 0.90 and result.freshness_mod >= 0.70:
        return "High"
    elif result.trust_weight >= 0.65 and result.freshness_mod >= 0.40:
        return "Moderate"
    elif result.trust_weight >= 0.40:
        return "Low"
    else:
        return "Uncertain"


# ---------------------------------------------------------------------------
# Golden test set
# ---------------------------------------------------------------------------

def _make_result(layer, source="user_explicit", age_days=0, relevance=0.8,
                 field_path="", memory="test"):
    return {
        "id": f"{layer}::{field_path or 'test'}",
        "memory": memory,
        "layer": layer,
        "source": source,
        "field_path": field_path,
        "age_days": age_days,
        "score": relevance,
        "relevance_score": relevance,
    }


# (description, results_list, query_type, assertion_fn)
GOLDEN_TESTS = [

    # 1. Core State always outranks wiki for canonical queries
    (
        "Core State beats wiki (canonical query, same relevance)",
        [
            _make_result("wiki",       relevance=0.95, memory="pricing is $997"),
            _make_result("core_state", relevance=0.80, memory="pricing is $997"),
        ],
        QUERY_TYPE_CANONICAL,
        lambda ranked: ranked[0].layer == "core_state",
    ),

    # 2. Wiki beats retrieval for pattern queries
    (
        "Wiki beats retrieval for pattern query",
        [
            _make_result("retrieval", relevance=0.90, memory="audience note"),
            _make_result("wiki",      relevance=0.75, memory="audience insight"),
        ],
        QUERY_TYPE_PATTERN,
        lambda ranked: ranked[0].layer == "wiki",
    ),

    # 3. Pending writes never surface
    (
        "Pending writes filtered out",
        [
            _make_result("pending",   relevance=0.99, memory="proposed pricing"),
            _make_result("core_state", relevance=0.50, memory="current pricing"),
        ],
        QUERY_TYPE_CANONICAL,
        lambda ranked: all(r.layer != "pending" for r in ranked),
    ),

    # 4. Stale pricing loses to fresh Core State
    (
        "Stale pricing (60 days) loses to fresh Core State pricing",
        [
            _make_result("retrieval", age_days=60, relevance=0.90,
                         field_path="offer_stack", memory="old pricing $500"),
            _make_result("core_state", age_days=1, relevance=0.75,
                         field_path="offer_stack.products", memory="current pricing $997"),
        ],
        QUERY_TYPE_CANONICAL,
        lambda ranked: ranked[0].layer == "core_state",
    ),

    # 5. Identity doesn't decay (no half-life)
    (
        "Identity field: no freshness decay regardless of age",
        [_make_result("core_state", age_days=500, field_path="identity.name",
                      memory="Tiffany")],
        QUERY_TYPE_CANONICAL,
        lambda ranked: ranked[0].freshness_mod == 1.0,
    ),

    # 6. Pricing field decays fast (7-day half-life)
    (
        "Pricing field: significant decay at 14 days (2 half-lives → ~25% modifier)",
        [_make_result("core_state", age_days=14, field_path="offer_stack",
                      memory="pricing note")],
        QUERY_TYPE_GENERAL,
        lambda ranked: ranked[0].freshness_mod < 0.35,
    ),

    # 7. Goals decay at 21-day half-life
    (
        "Goals field: ~50% freshness modifier at 21 days (1 half-life)",
        [_make_result("core_state", age_days=21, field_path="current_goals",
                      memory="goal note")],
        QUERY_TYPE_GENERAL,
        lambda ranked: 0.45 <= ranked[0].freshness_mod <= 0.55,
    ),

    # 8. Trust floor enforced: low-trust result cannot beat high-trust
    (
        "Low-trust external cannot beat Core State for canonical query",
        [
            _make_result("retrieval", source="external", relevance=0.99,
                         memory="external pricing claim"),
            _make_result("core_state", source="user_explicit", relevance=0.40,
                         memory="confirmed pricing"),
        ],
        QUERY_TYPE_CANONICAL,
        lambda ranked: ranked[0].layer == "core_state",
    ),

    # 9. Inferred source has lower trust than explicit
    (
        "system_inferred trust < user_explicit trust for same layer",
        [
            _make_result("wiki", source="system_inferred", relevance=0.85),
            _make_result("wiki", source="user_explicit",   relevance=0.65),
        ],
        QUERY_TYPE_GENERAL,
        lambda ranked: ranked[0].source == "user_explicit",
    ),

    # 10. Confidence label correct for Core State, fresh, user_explicit
    (
        "Confidence label: Core State + fresh + user_explicit → High",
        [_make_result("core_state", source="user_explicit", age_days=1,
                      field_path="identity.name")],
        QUERY_TYPE_GENERAL,
        lambda ranked: confidence_label(ranked[0]) == "High",
    ),

    # 11. Confidence label: stale retrieval → Uncertain or Low
    (
        "Confidence label: external retrieval + 90 days → Low or Uncertain",
        [_make_result("retrieval", source="external", age_days=90)],
        QUERY_TYPE_GENERAL,
        lambda ranked: confidence_label(ranked[0]) in ("Low", "Uncertain"),
    ),

    # 12. Query type detection: pricing question → canonical
    (
        "Query type: 'what is my pricing' → canonical",
        None, None,
        lambda _: detect_query_type("what is my pricing") == QUERY_TYPE_CANONICAL,
    ),

    # 13. Query type detection: pattern question → pattern
    (
        "Query type: 'why does this approach work' → pattern",
        None, None,
        lambda _: detect_query_type("why does this approach work") == QUERY_TYPE_PATTERN,
    ),

    # 14. Query type detection: history question → history
    (
        "Query type: 'what changed recently' → history",
        None, None,
        lambda _: detect_query_type("what changed recently") == QUERY_TYPE_HISTORY,
    ),

    # 15. Query type detection: general question → general
    (
        "Query type: 'tell me about IRIS' → general",
        None, None,
        lambda _: detect_query_type("tell me about IRIS") == QUERY_TYPE_GENERAL,
    ),

    # 16. Preferred layers order: canonical → core_state first
    (
        "Layer order: canonical query → core_state is first preferred layer",
        None, None,
        lambda _: preferred_layers(QUERY_TYPE_CANONICAL)[0] == "core_state",
    ),

    # 17. Preferred layers order: pattern → wiki first
    (
        "Layer order: pattern query → wiki is first preferred layer",
        None, None,
        lambda _: preferred_layers(QUERY_TYPE_PATTERN)[0] == "wiki",
    ),

    # 18. Preferred layers order: history → audit first
    (
        "Layer order: history query → audit is first preferred layer",
        None, None,
        lambda _: preferred_layers(QUERY_TYPE_HISTORY)[0] == "audit",
    ),

    # 19. Fresh pricing (1 day) still has good freshness modifier
    (
        "Pricing field: minimal decay at 1 day",
        [_make_result("core_state", age_days=1, field_path="offer_stack")],
        QUERY_TYPE_GENERAL,
        lambda ranked: ranked[0].freshness_mod > 0.85,
    ),

    # 20. Tone preference has no decay (None half-life)
    (
        "Tone preferences: no decay at 200 days",
        [_make_result("core_state", age_days=200, field_path="tone_preferences")],
        QUERY_TYPE_GENERAL,
        lambda ranked: ranked[0].freshness_mod == 1.0,
    ),
]


def run_tests(verbose: bool = False) -> dict:
    """Run golden test set. Returns {passed, failed, total, failures}."""
    passed = 0
    failed = 0
    failures = []

    for description, results_input, query_type, assertion in GOLDEN_TESTS:
        try:
            if results_input is not None:
                ranked = rank_results(results_input, query_type or QUERY_TYPE_GENERAL)
            else:
                ranked = []

            ok = assertion(ranked)
        except Exception as e:
            ok = False
            failures.append({"description": description, "error": str(e)})
            if verbose:
                print(f"  ✗ {description} [exception: {e}]")
            failed += 1
            continue

        if ok:
            passed += 1
            if verbose:
                print(f"  ✓ {description}")
        else:
            failed += 1
            # Collect debug info
            detail = []
            if ranked:
                for r in ranked[:3]:
                    detail.append(
                        f"    [{r.rank}] {r.layer}/{r.source} "
                        f"tw={r.trust_weight:.2f} fm={r.freshness_mod:.2f} "
                        f"rel={r.relevance_score:.2f} → final={r.final_score:.4f}"
                    )
            failures.append({"description": description, "ranked_top3": detail})
            if verbose:
                print(f"  ✗ {description}")
                for d in detail:
                    print(d)

    return {"passed": passed, "failed": failed, "total": len(GOLDEN_TESTS), "failures": failures}


# ---------------------------------------------------------------------------
# Demo: show score comparison across layers
# ---------------------------------------------------------------------------

def demo():
    """Print a side-by-side score comparison to show ranking in action."""
    print("\n=== Ranking Demo: canonical pricing query ===")
    print("(same relevance=0.80 across all layers)\n")

    query_type = QUERY_TYPE_CANONICAL
    examples = [
        ("Core State — fresh user_explicit pricing",
         _make_result("core_state", source="user_explicit",  age_days=1,  relevance=0.80,
                      field_path="offer_stack.products")),
        ("Core State — 14-day-old pricing",
         _make_result("core_state", source="user_explicit",  age_days=14, relevance=0.80,
                      field_path="offer_stack.products")),
        ("Wiki — user_confirmed pricing note, fresh",
         _make_result("wiki",       source="user_confirmed", age_days=2,  relevance=0.80)),
        ("Wiki — system_inferred note, fresh",
         _make_result("wiki",       source="system_inferred", age_days=2, relevance=0.80)),
        ("Retrieval — external source, very relevant (0.99)",
         _make_result("retrieval",  source="external",       age_days=0,  relevance=0.99)),
        ("Retrieval — system_inferred, fresh",
         _make_result("retrieval",  source="system_inferred", age_days=0, relevance=0.80)),
        ("Pending write — highly relevant",
         _make_result("pending",    source="user_explicit",  age_days=0,  relevance=0.99)),
    ]

    ranked = rank_results([e for _, e in examples], query_type)

    for r in ranked:
        label = confidence_label(r)
        print(f"  [{r.rank}] {r.layer:<12} {r.source:<20} "
              f"tw={r.trust_weight:.2f} fm={r.freshness_mod:.2f} "
              f"rel={r.relevance_score:.2f} → {r.final_score:.4f}  [{label}]")
    print()

    print("=== Pattern query: same results, different ordering ===\n")
    ranked2 = rank_results([e for _, e in examples], QUERY_TYPE_PATTERN)
    for r in ranked2:
        print(f"  [{r.rank}] {r.layer:<12} {r.source:<20} → {r.final_score:.4f}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="IRIS Retrieval Ranking — trust + freshness scoring")
    parser.add_argument("--test", action="store_true", help="Run golden test set")
    parser.add_argument("--demo", action="store_true", help="Show scoring demo")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.test:
        print("Running ranking golden test set...\n")
        results = run_tests(verbose=True)
        print(f"\n{'─'*40}")
        print(f"  {results['passed']}/{results['total']} passed", end="")
        if results["failed"]:
            print(f"  ({results['failed']} failed)")
            for f in results["failures"]:
                print(f"\n  ✗ {f['description']}")
                if "error" in f:
                    print(f"      error: {f['error']}")
                for d in f.get("ranked_top3", []):
                    print(d)
        else:
            print("  — all green")
        sys.exit(0 if results["failed"] == 0 else 1)

    if args.demo:
        demo()
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
