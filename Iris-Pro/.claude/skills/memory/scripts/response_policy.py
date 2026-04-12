#!/usr/bin/env python3
"""
response_policy.py — Phase 5: Response Behavior + Memory Usage Policy

Programmatic decision logic for when and how IRIS uses memory in live conversation.

Three responsibilities:
  1. decide_usage_mode()  — which of the 4 modes applies to a given context
  2. citation_phrase()    — how to phrase memory when it must be surfaced
  3. should_surface_pattern() — whether a recurring pattern threshold is met

The 4 modes (from .claude/rules/memory-usage-policy.md):
  - silent  : use the memory, do not mention it
  - cite    : surface it explicitly because transparency helps
  - confirm : ask before proceeding (contradiction, stale + decision, update detected)
  - ignore  : do not use stored context, answer directly

Usage:
    python3 response_policy.py --test           # run golden test set
    python3 response_policy.py --scenario       # print all 20 scenario decisions
"""

import sys
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Mode constants
# ---------------------------------------------------------------------------
MODE_SILENT  = "silent"
MODE_CITE    = "cite"
MODE_CONFIRM = "confirm"
MODE_IGNORE  = "ignore"

# ---------------------------------------------------------------------------
# Context dataclass — what IRIS knows going into a response
# ---------------------------------------------------------------------------

@dataclass
class ResponseContext:
    """Everything that informs a memory-use decision for one response."""
    # About the current query
    query_type: str = "general"       # canonical | pattern | history | general
    is_task_execution: bool = False   # user wants a thing done, not context
    is_emotional: bool = False        # user is venting, frustrated, or upset

    # About the memory hit
    has_memory_match: bool = False    # did retrieval return something relevant?
    memory_layer: str = ""            # core_state | wiki | retrieval | pending | none
    memory_source: str = "unknown"    # user_explicit | user_confirmed | system_inferred | external
    confidence: str = "low"          # high | moderate | low | uncertain
    is_stale: bool = False            # is the matched field past its staleness window?
    stale_shown_this_session: bool = False  # already surfaced this stale flag today

    # About what the user just said
    user_is_updating: bool = False    # user statement looks like a canonical update
    user_contradicts_memory: bool = False  # what user said contradicts stored fact

    # About patterns
    pattern_count: int = 0            # how many times this pattern has appeared
    pattern_surfaced_recently: bool = False  # shown in last 7 days

    # About pending writes
    pending_write_triggered: bool = False  # ingest.py queued a write for this input


# ---------------------------------------------------------------------------
# Core decision function
# ---------------------------------------------------------------------------

def decide_usage_mode(ctx: ResponseContext) -> tuple[str, str]:
    """
    Return (mode, reason) for a given response context.

    Priority order (checked in sequence):
      1. Emotional / venting → always ignore
      2. Pending write or update detected → confirm
      3. Contradiction with Core State → confirm
      4. Stale + decision-bearing → confirm (once per session)
      5. Task execution → silent (apply preferences without mention)
      6. Canonical query + high-confidence Core State → silent
      7. Strategy/reasoning query or wiki-level memory → cite
      8. Low-confidence or inferred memory → ignore
      9. Default → silent if match, ignore if no match
    """

    # Gate 1: emotional state → ignore always
    if ctx.is_emotional:
        return MODE_IGNORE, "user is emotional or venting — do not surface memory"

    # Gate 2: pending write triggered → confirm
    if ctx.pending_write_triggered:
        return MODE_CONFIRM, "ingest pipeline detected a canonical update in user input"

    # Gate 3: user statement contradicts stored fact → confirm
    if ctx.user_contradicts_memory:
        return MODE_CONFIRM, "user statement contradicts stored Core State value"

    # Gate 4: stale field + user is making a decision with it → confirm (once per session)
    if ctx.is_stale and ctx.has_memory_match and not ctx.stale_shown_this_session:
        if ctx.query_type == "canonical" or ctx.user_is_updating:
            return MODE_CONFIRM, "stored fact is stale and user is making a decision from it"

    # Gate 5: task execution → silent
    if ctx.is_task_execution:
        return MODE_SILENT, "task execution — apply memory silently, do not narrate it"

    # Gate 6: canonical query + high-confidence Core State → silent
    if (ctx.query_type == "canonical"
            and ctx.memory_layer == "core_state"
            and ctx.confidence in ("high",)
            and not ctx.is_stale):
        return MODE_SILENT, "direct canonical question answered by fresh Core State fact"

    # Gate 7: no memory match → ignore
    if not ctx.has_memory_match or ctx.memory_layer in ("none", "pending", ""):
        return MODE_IGNORE, "no relevant memory match — answer directly"

    # Gate 8: inferred or external source → ignore (never cite as fact)
    if ctx.memory_source in ("system_inferred", "external"):
        return MODE_IGNORE, "inferred/external source — cannot cite as user fact"

    # Gate 9: low confidence → ignore
    if ctx.confidence in ("low", "uncertain"):
        return MODE_IGNORE, "low-confidence match — do not cite, answer directly or ask"

    # Gate 10: strategy / pattern / history query, or wiki-level source → cite
    if ctx.query_type in ("pattern", "history") or ctx.memory_layer in ("wiki", "retrieval"):
        return MODE_CITE, "strategy/pattern/history query or wiki-level source — surface with framing"

    # Gate 11: canonical query but stale (already shown this session) → cite
    if ctx.is_stale and ctx.stale_shown_this_session:
        return MODE_CITE, "stale flag already shown — cite with caveat, do not re-confirm"

    # Gate 12: moderate confidence Core State → cite (worth mentioning source)
    if ctx.memory_layer == "core_state" and ctx.confidence == "moderate":
        return MODE_CITE, "moderate-confidence Core State — cite to give user chance to correct"

    # Default: if we have a good match and no reason to hide it → silent
    return MODE_SILENT, "default — good match, no reason to surface the retrieval"


# ---------------------------------------------------------------------------
# Pattern surfacing decision
# ---------------------------------------------------------------------------

def should_surface_pattern(
    pattern_count: int,
    is_emotional: bool,
    is_task_execution: bool,
    pattern_surfaced_recently: bool,
    query_type: str,
) -> tuple[bool, str]:
    """
    Return (should_surface, reason).
    Threshold: 3+ instances, not emotional, not task execution, not recently shown,
    and in strategy/reflection mode.
    """
    if is_emotional:
        return False, "never surface patterns during emotional state"
    if is_task_execution:
        return False, "never surface patterns during task execution"
    if pattern_surfaced_recently:
        return False, "pattern surfaced in last 7 days — do not repeat"
    if pattern_count < 3:
        return False, f"pattern count {pattern_count} below threshold of 3"
    if query_type not in ("pattern", "history", "general"):
        return False, "only surface patterns in strategy/reflection/general context"
    return True, f"pattern count {pattern_count} ≥ 3 and context is appropriate"


# ---------------------------------------------------------------------------
# Citation phrase builder
# ---------------------------------------------------------------------------

def citation_phrase(
    memory_layer: str,
    source: str,
    field_path: str = "",
    is_stale: bool = False,
    stale_date: str = "",
    value_summary: str = "",
) -> str:
    """
    Return a natural-language citation phrase appropriate for the memory type.

    Principles:
    - Core State fresh: no citation (caller should use silent mode)
    - Core State stale: gentle date-anchored question
    - Wiki synthesis: framed as working understanding
    - Retrieval: flagged as prior context worth checking
    - Inferred: never called (caller should use ignore mode)
    """
    if memory_layer == "core_state" and is_stale:
        if stale_date:
            return f"The last time you confirmed this was {stale_date} — is that still current?"
        return "This was set a while back — is it still accurate?"

    if memory_layer == "core_state" and not is_stale:
        # Silent mode should have been used; if cite was chosen anyway, keep it minimal
        if value_summary:
            return f"You've set {value_summary} — working from that."
        return ""

    if memory_layer == "wiki":
        if value_summary:
            return f"From what you've shared about this, {value_summary}."
        return "From what you've shared on this topic, my working understanding is:"

    if memory_layer == "retrieval":
        if value_summary:
            return f"This came up before ({value_summary}) — worth checking if it still applies."
        return "This came up in a prior context — worth checking if it still applies."

    if source == "system_inferred":
        # Should never be called — ignore mode blocks inferred. Defensive fallback.
        return ""

    if memory_layer in ("pending", "none", ""):
        return ""

    # Generic fallback
    if value_summary:
        return f"Based on what you've shared: {value_summary}."
    return ""


def pattern_phrase(observation: str, count: int) -> str:
    """
    Return a natural-language pattern observation phrase.
    Does not accuse. Does not predict failure. Frames as observation, not coaching.
    """
    if not observation:
        return ""
    return f"I've noticed this come up a few times: {observation}. Worth naming?"


# ---------------------------------------------------------------------------
# Golden test set — 20 conversation scenarios
# ---------------------------------------------------------------------------

GOLDEN_SCENARIOS = [
    # (label, context_kwargs, expected_mode)

    # --- Task execution → silent ---
    ("draft email — task execution, high confidence",
     dict(is_task_execution=True, has_memory_match=True, memory_layer="core_state",
          memory_source="user_explicit", confidence="high"),
     MODE_SILENT),

    ("write LinkedIn post — task, voice preferences in memory",
     dict(is_task_execution=True, has_memory_match=True, memory_layer="core_state",
          confidence="high"),
     MODE_SILENT),

    # --- Canonical query, fresh Core State → silent ---
    ("'what is my pricing' — canonical, fresh Core State",
     dict(query_type="canonical", has_memory_match=True, memory_layer="core_state",
          memory_source="user_explicit", confidence="high", is_stale=False),
     MODE_SILENT),

    ("'what is my goal' — canonical, fresh Core State",
     dict(query_type="canonical", has_memory_match=True, memory_layer="core_state",
          confidence="high", is_stale=False),
     MODE_SILENT),

    # --- Emotional → always ignore ---
    ("user is venting frustration — ignore everything",
     dict(is_emotional=True, has_memory_match=True, memory_layer="core_state",
          confidence="high"),
     MODE_IGNORE),

    ("user frustrated with testing — do not pull commitment history",
     dict(is_emotional=True, has_memory_match=True, memory_layer="wiki",
          query_type="pattern"),
     MODE_IGNORE),

    # --- Contradiction detected → confirm ---
    ("user says new price contradicts stored price",
     dict(user_contradicts_memory=True, has_memory_match=True,
          memory_layer="core_state", confidence="high"),
     MODE_CONFIRM),

    # --- User updating something → confirm ---
    ("user says 'my goal has changed' — pending write triggered",
     dict(pending_write_triggered=True, has_memory_match=True,
          memory_layer="core_state"),
     MODE_CONFIRM),

    # --- Stale + decision → confirm (once per session) ---
    ("stale pricing, user making pricing decision",
     dict(query_type="canonical", has_memory_match=True, memory_layer="core_state",
          confidence="high", is_stale=True, stale_shown_this_session=False),
     MODE_CONFIRM),

    # --- Stale but already confirmed this session → cite ---
    ("stale pricing, stale already shown this session",
     dict(query_type="canonical", has_memory_match=True, memory_layer="core_state",
          confidence="high", is_stale=True, stale_shown_this_session=True),
     MODE_CITE),

    # --- Strategy/pattern query → cite ---
    ("'why does this keep happening' — pattern query + wiki",
     dict(query_type="pattern", has_memory_match=True, memory_layer="wiki",
          memory_source="user_explicit", confidence="moderate"),
     MODE_CITE),

    ("'what worked for my audience positioning' — pattern query",
     dict(query_type="pattern", has_memory_match=True, memory_layer="wiki",
          confidence="high"),
     MODE_CITE),

    # --- History query → cite ---
    ("'what changed recently' — history query",
     dict(query_type="history", has_memory_match=True, memory_layer="core_state",
          confidence="high"),
     MODE_CITE),

    # --- No memory match → ignore ---
    ("'how does Pinecone pricing work' — general, no match",
     dict(has_memory_match=False, query_type="general"),
     MODE_IGNORE),

    ("'what is the weather' — no relevant memory",
     dict(has_memory_match=False),
     MODE_IGNORE),

    # --- Inferred source → ignore ---
    ("AI inferred a preference — never cite as fact",
     dict(has_memory_match=True, memory_layer="wiki",
          memory_source="system_inferred", confidence="moderate"),
     MODE_IGNORE),

    # --- External source → ignore ---
    ("external article summary — not user belief",
     dict(has_memory_match=True, memory_layer="retrieval",
          memory_source="external", confidence="moderate"),
     MODE_IGNORE),

    # --- Low confidence → ignore ---
    ("low confidence retrieval match — don't cite",
     dict(has_memory_match=True, memory_layer="retrieval",
          memory_source="user_explicit", confidence="low"),
     MODE_IGNORE),

    # --- Moderate Core State → cite ---
    ("moderate confidence Core State — surface with framing",
     dict(query_type="canonical", has_memory_match=True, memory_layer="core_state",
          memory_source="user_confirmed", confidence="moderate", is_stale=False),
     MODE_CITE),

    # --- Pending layer → ignore ---
    ("pending write in memory layer — never surface as truth",
     dict(has_memory_match=True, memory_layer="pending", confidence="high"),
     MODE_IGNORE),
]


def run_tests(verbose: bool = False) -> dict:
    """Run golden scenario test set. Returns {passed, failed, total, failures}."""
    passed = 0
    failed = 0
    failures = []

    for label, ctx_kwargs, expected_mode in GOLDEN_SCENARIOS:
        ctx = ResponseContext(**ctx_kwargs)
        mode, reason = decide_usage_mode(ctx)

        if mode == expected_mode:
            passed += 1
            if verbose:
                print(f"  ✓ [{mode:7}] {label}")
        else:
            failed += 1
            failures.append({
                "label": label,
                "expected": expected_mode,
                "got": mode,
                "reason": reason,
            })
            if verbose:
                print(f"  ✗ [{mode:7}] {label}")
                print(f"           expected: {expected_mode}")
                print(f"           reason:   {reason}")

    return {"passed": passed, "failed": failed, "total": len(GOLDEN_SCENARIOS), "failures": failures}


# ---------------------------------------------------------------------------
# Scenario print (all 20 with full decision output)
# ---------------------------------------------------------------------------

def print_scenarios():
    print("\n=== All 20 conversation scenarios ===\n")
    for label, ctx_kwargs, expected_mode in GOLDEN_SCENARIOS:
        ctx = ResponseContext(**ctx_kwargs)
        mode, reason = decide_usage_mode(ctx)
        mark = "✓" if mode == expected_mode else "✗"
        print(f"  {mark} [{mode:7}] {label}")
        if mode != expected_mode:
            print(f"           EXPECTED {expected_mode}")
        # Show a sample citation phrase for cite mode
        if mode == MODE_CITE:
            phrase = citation_phrase(
                ctx.memory_layer, ctx.memory_source,
                is_stale=ctx.is_stale
            )
            if phrase:
                print(f"           phrase: \"{phrase}\"")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="IRIS Response Policy — memory usage decisions")
    parser.add_argument("--test",     action="store_true", help="Run golden test set")
    parser.add_argument("--scenario", action="store_true", help="Print all 20 scenario decisions")
    parser.add_argument("--verbose",  action="store_true")
    args = parser.parse_args()

    if args.test:
        print("Running response policy golden test set...\n")
        results = run_tests(verbose=True)
        print(f"\n{'─'*40}")
        print(f"  {results['passed']}/{results['total']} passed", end="")
        if results["failed"]:
            print(f"  ({results['failed']} failed)")
            for f in results["failures"]:
                print(f"\n  ✗ {f['label']}")
                print(f"      expected: {f['expected']}, got: {f['got']}")
                print(f"      reason:   {f['reason']}")
        else:
            print("  — all green")
        sys.exit(0 if results["failed"] == 0 else 1)

    if args.scenario:
        print_scenarios()
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
