#!/usr/bin/env python3
"""
ingest.py — Phase 3: Classify-and-Route Ingest Pipeline

Three separate decisions, in order:
  1. Is this memory-worthy?          (is_memory_worthy)
  2. What type of memory is it?      (classify)
  3. If Core State candidate, write/queue/block?  (promote → plugs into core_state.py)

Never combine classify + promote into one step.
Default stance: drop, not queue. Queue volume is a failure signal.

Usage:
  python3 ingest.py --text "my price is now $997" --source user_explicit --actor tiffany
  python3 ingest.py --text "..." --source system_inferred --dry-run
  python3 ingest.py --pending          # show queued ingest decisions needing review
  python3 ingest.py --test             # run golden test set
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_ROOT = _HERE.parents[3]  # Iris-Pro root

INGEST_LOG_PATH = _ROOT / "memory" / "ingest-log.jsonl"
INGEST_QUEUE_PATH = _ROOT / "memory" / "ingest-queue.jsonl"

# ---------------------------------------------------------------------------
# Routing classes — keep small, do not over-taxonomize
# ---------------------------------------------------------------------------
CLASS_CANONICAL_FACT = "canonical_fact"      # → Core State candidate
CLASS_PREFERENCE     = "preference"          # → Core State candidate
CLASS_CURRENT_STATE  = "current_state"       # → Core State candidate (short-lived)
CLASS_PROJECT_CTX    = "project_context"     # → Core State active_project_context
CLASS_REF_KNOWLEDGE  = "reference_knowledge" # → wiki
CLASS_RETRIEVAL_ONLY = "retrieval_only"      # → Pinecone/index only (never Core)
CLASS_NOISE          = "noise"               # → drop

CORE_STATE_CLASSES = {CLASS_CANONICAL_FACT, CLASS_PREFERENCE, CLASS_CURRENT_STATE, CLASS_PROJECT_CTX}

# Destination constants
DEST_CORE_STATE     = "core_state"
DEST_WIKI           = "wiki"
DEST_RETRIEVAL      = "retrieval"
DEST_DROP           = "drop"

# ---------------------------------------------------------------------------
# Decision dataclass — one per ingested item, everything explained
# ---------------------------------------------------------------------------
@dataclass
class IngestDecision:
    item_id: str
    timestamp: str
    source: str            # user_explicit | user_confirmed | system_inferred | system_canonical | external
    actor: str             # who/what produced this (tiffany, telegram_handler, compiler, etc.)
    raw_text: str
    # Stage 1
    memory_worthy: str     # yes | maybe | no
    # Stage 2
    classification: str    # routing class (see CLASS_* constants)
    # Stage 3
    destination: str       # core_state | wiki | retrieval | drop
    confidence: float      # 0.0–1.0, grounded in source type
    promotion_eligibility: str  # immediate | queue | block | n/a
    reason: str            # human-readable explanation
    evidence_span: str     # the specific substring that drove classification
    policy_result: Optional[str] = None   # filled in when promotion attempted
    final_disposition: Optional[str] = None  # accepted | queued | blocked | dropped | logged
    suggested_field: Optional[str] = None    # Core State field path if canonical_fact/preference
    dry_run: bool = False

# ---------------------------------------------------------------------------
# Stage 1: Is this memory-worthy?
# ---------------------------------------------------------------------------

# Signals that a message is almost certainly noise — checked before classification
_NOISE_PATTERNS = [
    # Ultra-short inputs
    lambda t: len(t.strip()) < 8,
    # Pure acknowledgements
    lambda t: t.strip().lower() in {"ok", "okay", "yes", "no", "yep", "nope", "sure",
                                     "cool", "great", "thanks", "k", "lol", "haha",
                                     "hmm", "hm", "got it", "sounds good", "nice"},
    # Test/junk strings
    lambda t: t.strip().lower() in {"test", "testing", "123", "hello", "hi", "hey"},
]

# Phrases that signal transient emotion or passing state — not durable facts
_EMOTION_NOISE_PHRASES = [
    "i'm frustrated", "i am frustrated", "so frustrated",
    "i'm annoyed", "i'm tired", "i'm exhausted",
    "i'm excited about", "i'm nervous about", "i'm worried about",
    "i feel like", "feeling like", "i just feel",
    "ugh", "ugh ", "argh", "sigh",
]

# Phrases that introduce meta-observations or insights — route to wiki not Core State
# even if they contain canonical entity mentions
_META_OBSERVATION_PREFIXES = [
    "the approach that", "the approach is", "an approach that",
    "the idea is", "the idea that", "my idea is",
    "the insight is", "the insight that",
    "what works best", "what works for",
    "the thing that works", "the best way to",
    "i've noticed that", "i've found that", "i've learned that",
    "it turns out", "turns out that",
    "the pattern is", "a pattern i've noticed",
]

# Strong signals of memory value
_MEMORY_SIGNALS = [
    "my price", "i charge", "pricing", "my product", "my offer",
    "my goal", "i want to", "i'm trying to", "i need to",
    "my name is", "i am", "i work", "my business", "my company",
    "the business is", "business is called", "business name",
    "i prefer", "i like", "i don't like", "i hate", "i love",
    "my audience", "my customer", "my client",
    "deadline", "by friday", "by monday", "this week", "due",
    "committed", "i promised", "i said i would",
    "always", "never", "don't ever", "make sure you",
    "my style", "my voice", "my tone",
    "the reason", "because", "the strategy", "the plan",
    "probably $", "maybe $", "around $", "enterprise tier", "pro tier",
]

# Signals that something is retrieval-worthy but not Core-worthy
_RETRIEVAL_SIGNALS = [
    "article", "read", "blog post", "paper", "source", "link",
    "according to", "research shows", "it says", "they say",
    "meeting notes", "transcript", "summary of",
    "someone said", "they mentioned",
]


def is_memory_worthy(text: str, source: str) -> tuple[str, str]:
    """
    Stage 1: Decide if this input has any memory value at all.
    Returns (verdict, reason) where verdict is 'yes' | 'maybe' | 'no'.

    Default is 'no'. Only escalate with positive signal.
    """
    t = text.strip()

    # Hard noise checks
    for check in _NOISE_PATTERNS:
        if check(t):
            return "no", "matches noise pattern (too short, filler, or junk)"

    # system_inferred and external sources get a higher bar
    if source in ("system_inferred", "external"):
        # Need a strong explicit signal even to be 'maybe'
        tl = t.lower()
        if any(sig in tl for sig in _MEMORY_SIGNALS):
            return "maybe", "inferred source but contains memory signal — needs confirmation before promotion"
        if any(sig in tl for sig in _RETRIEVAL_SIGNALS):
            return "maybe", "external/inferred source — retrieval candidate only"
        return "no", "inferred/external source with no clear memory signal"

    # user_explicit and user_confirmed get more benefit of the doubt
    if source in ("user_explicit", "user_confirmed"):
        tl = t.lower()
        # Transient emotion → drop even if user_explicit
        if any(sig in tl for sig in _EMOTION_NOISE_PHRASES):
            return "no", "transient emotional state — not a durable fact"
        if any(sig in tl for sig in _MEMORY_SIGNALS):
            return "yes", "user source with strong memory signal"
        if len(t) > 40:
            return "maybe", "user source, no strong signal but substantive length"
        return "no", "user source but no identifiable memory signal in short input"

    # system_canonical: always memory-worthy (comes from approved workflows)
    if source == "system_canonical":
        return "yes", "system_canonical source — approved workflow output"

    # Unknown source — conservative
    return "no", "unrecognized source — dropping conservatively"


# ---------------------------------------------------------------------------
# Stage 2: Classify — what TYPE of memory is this?
# ---------------------------------------------------------------------------

# Explicit field-name signals → canonical_fact or preference
# ORDER MATTERS: more specific / higher-priority fields first.
# The first signal match wins. Put operational/project context before goals
# so "working on X" doesn't bleed into goals.
_FIELD_SIGNALS: dict[str, list[str]] = {
    "active_project_context":     ["current project", "right now i'm working on", "this sprint",
                                   "the project is", "currently building", "working on"],
    "active_commitments":         ["i promised", "i committed", "i said i would", "i need to do",
                                   "by friday", "by monday", "deadline"],
    "identity.name":              ["my name is", "i'm called", "call me"],
    "identity.business_name":     ["my business is", "my company is", "the business is called",
                                   "the business name", "business is called"],
    "identity.role":              ["my role is", "i'm a ", "i am a "],
    "current_goals.primary":      ["my goal is", "i'm trying to", "my main focus", "my priority is",
                                   "i want to", "my top priority", "i'm focused on",
                                   "the goal is", "main thing i'm"],
    "offer_stack.products":       ["my price", "i charge", "my offer", "my product",
                                   "the cost is", "it costs", "let's go with $",
                                   "i should charge", "i'm charging", "bump it to $",
                                   "one-time", "per month", "monthly fee"],
    "tone_preferences.avoid":     ["don't ever", "never use", "avoid", "don't say", "stop saying"],
    "tone_preferences.writing_voice": ["my writing voice is", "my voice is", "my tone is",
                                       "my style is", "write like"],
    "canonical_business_facts.target_audience": ["my audience", "my customer", "my client",
                                                  "i sell to", "my user is"],
}

# Signals for tentative / hedged pricing/fact statements — still canonical_fact
# but route to queue (not immediate)
_TENTATIVE_PRICE_SIGNALS = [
    "probably $", "maybe $", "around $", "roughly $", "about $",
    "enterprise tier", "enterprise plan", "pro tier", "pro plan",
]


def classify(text: str, source: str) -> tuple[str, float, str, str]:
    """
    Stage 2: Classify what type of memory this is.
    Returns (classification, confidence, reason, evidence_span).

    Confidence is grounded in source type, not model vibes:
      user_explicit → 0.85–0.95
      user_confirmed → 0.80–0.90
      system_canonical → 0.90–0.95
      system_inferred → 0.40–0.60
      external → 0.30–0.50

    Check order (matters — earlier checks win):
      1. Retrieval signals — external/reference content never promotes to Core State
      2. Meta-observation prefixes — insights/observations route to wiki even if they mention
         canonical entities ("The approach that works best for my audience...")
      3. Tentative price/fact signals — still canonical_fact but confidence capped
      4. Field signals — specific Core State field patterns
      5. Reference knowledge signals — explanatory content
      6. Fallback
    """
    tl = text.lower()

    # Base confidence by source
    base = {
        "user_explicit":    0.88,
        "user_confirmed":   0.83,
        "system_canonical": 0.92,
        "system_inferred":  0.50,
        "external":         0.40,
    }.get(source, 0.45)

    # PRE-CHECK 1: Retrieval signals — external/reference content, meeting notes, transcripts
    # These win before field signals to prevent "meeting notes about pricing" → Core State
    for sig in _RETRIEVAL_SIGNALS:
        if sig in tl:
            return CLASS_RETRIEVAL_ONLY, min(base, 0.55), \
                   f"matches retrieval signal '{sig}' — reference content only", sig

    # PRE-CHECK 2: Meta-observation prefixes — route to wiki even if they mention canonical entities
    # "The approach that works best for my audience..." should NOT fire canonical_fact
    for prefix in _META_OBSERVATION_PREFIXES:
        if tl.startswith(prefix) or f" {prefix}" in tl:
            return CLASS_REF_KNOWLEDGE, min(base, 0.72), \
                   f"meta-observation prefix '{prefix}' — insight/observation routes to wiki", prefix

    # PRE-CHECK 3: Tentative/hedged pricing or fact signals
    # Still canonical_fact (user is talking about pricing) but confidence capped low → queued
    for sig in _TENTATIVE_PRICE_SIGNALS:
        if sig in tl:
            return CLASS_CANONICAL_FACT, min(base, 0.60), \
                   f"tentative fact signal '{sig}' — canonical_fact but low confidence, will queue", sig

    # MAIN CHECK: Specific Core State field signals
    for field_path, signals in _FIELD_SIGNALS.items():
        for sig in signals:
            if sig in tl:
                # Determine class from field path
                if "commitment" in field_path:
                    return CLASS_CURRENT_STATE, min(base, 0.85), \
                           f"matches commitment signal '{sig}'", sig
                if "project_context" in field_path:
                    return CLASS_PROJECT_CTX, min(base, 0.85), \
                           f"matches project context signal '{sig}'", sig
                if "preference" in field_path or "tone" in field_path or "avoid" in field_path:
                    return CLASS_PREFERENCE, base, \
                           f"matches preference signal '{sig}' → {field_path}", sig
                # Everything else is canonical_fact
                return CLASS_CANONICAL_FACT, base, \
                       f"matches canonical fact signal '{sig}' → {field_path}", sig

    # Reference knowledge: explanatory content, strategy, plan, reasoning
    ref_signals = ["the reason", "because", "the strategy", "the approach", "how to", "why ",
                   "the plan is", "the idea is", "the concept", "this works by",
                   "i've been thinking", "thinking about maybe", "i think that"]
    for sig in ref_signals:
        if sig in tl:
            return CLASS_REF_KNOWLEDGE, min(base, 0.70), \
                   f"explanatory content signal '{sig}' → wiki", sig

    # Fallback: if source is user and it was memory-worthy, call it reference knowledge
    if source in ("user_explicit", "user_confirmed"):
        return CLASS_REF_KNOWLEDGE, 0.60, \
               "user source, memory-worthy, no strong class signal — defaulting to reference_knowledge", ""

    # Inferred with no clear class → noise
    return CLASS_NOISE, 0.80, "no classification signal found — dropping", ""


# ---------------------------------------------------------------------------
# Stage 2b: Suggest Core State field path for canonical_fact/preference
# ---------------------------------------------------------------------------

def suggest_field(text: str) -> Optional[str]:
    """Return the most likely Core State field path for this text, or None."""
    tl = text.lower()
    # Check field signals first (more specific)
    for field_path, signals in _FIELD_SIGNALS.items():
        for sig in signals:
            if sig in tl:
                return field_path
    # Tentative price signals → offer_stack.products
    for sig in _TENTATIVE_PRICE_SIGNALS:
        if sig in tl:
            return "offer_stack.products"
    return None


# ---------------------------------------------------------------------------
# Stage 2c: Route — where does this go?
# ---------------------------------------------------------------------------

def route(classification: str, source: str) -> tuple[str, str]:
    """
    Stage 2c: Given a classification, return (destination, promotion_eligibility).
    Destination: core_state | wiki | retrieval | drop
    Promotion eligibility: immediate | queue | block | n/a
    """
    if classification == CLASS_NOISE:
        return DEST_DROP, "n/a"

    if classification in (CLASS_CANONICAL_FACT, CLASS_PREFERENCE):
        if source == "user_explicit":
            return DEST_CORE_STATE, "queue"       # still queue — on_change policy requires confirmation
        if source == "user_confirmed":
            return DEST_CORE_STATE, "queue"
        if source == "system_canonical":
            return DEST_CORE_STATE, "immediate"   # approved workflow, can write directly
        if source == "system_inferred":
            return DEST_CORE_STATE, "block"       # inferred never writes Core State
        return DEST_CORE_STATE, "block"

    if classification == CLASS_CURRENT_STATE:
        if source in ("user_explicit", "user_confirmed", "system_canonical"):
            return DEST_CORE_STATE, "queue"
        return DEST_CORE_STATE, "block"

    if classification == CLASS_PROJECT_CTX:
        if source in ("user_explicit", "user_confirmed", "system_canonical"):
            return DEST_CORE_STATE, "queue"
        return DEST_CORE_STATE, "block"

    if classification == CLASS_REF_KNOWLEDGE:
        return DEST_WIKI, "n/a"

    if classification == CLASS_RETRIEVAL_ONLY:
        return DEST_RETRIEVAL, "n/a"

    return DEST_DROP, "n/a"


# ---------------------------------------------------------------------------
# Stage 3: Attempt promotion to Core State via core_state.py
# ---------------------------------------------------------------------------

def attempt_promotion(decision: IngestDecision) -> IngestDecision:
    """
    Stage 3: If destination is core_state, hand off to core_state.py write() rules.
    Uses queue_write() so field policies and confirmation gates apply.
    Does NOT write directly — always goes through the Phase 2 gate.
    """
    # Wiki destination → write to wiki layer
    if decision.destination == DEST_WIKI:
        try:
            sys.path.insert(0, str(_HERE))
            import wiki
            result = wiki.write_page(
                title=decision.raw_text[:80],
                content=decision.raw_text,
                entity_type="synthesis",
                author_type=decision.source,
                confidence=decision.confidence,
                source_ids=[decision.item_id],
                tags=[decision.classification],
            )
            decision.policy_result = f"wiki page {result['status']}: {result['slug']}"
            decision.final_disposition = "logged"
        except Exception as e:
            decision.policy_result = f"wiki write error: {e}"
            decision.final_disposition = "error"
        return decision

    if decision.destination not in (DEST_CORE_STATE,):
        decision.final_disposition = "dropped" if decision.destination == DEST_DROP else "logged"
        return decision

    if decision.promotion_eligibility == "block":
        decision.policy_result = f"blocked: source '{decision.source}' cannot write Core State"
        decision.final_disposition = "blocked"
        return decision

    if decision.dry_run:
        decision.policy_result = "dry_run — no write attempted"
        decision.final_disposition = "dry_run"
        return decision

    # Import here to avoid circular dependency risk
    try:
        sys.path.insert(0, str(_HERE))
        import core_state

        field = decision.suggested_field
        if not field:
            # Can't promote without a field path — log for review
            decision.policy_result = "no suggested_field — cannot route to Core State without field path"
            decision.final_disposition = "queued_for_review"
            _append_ingest_queue(decision)
            return decision

        result = core_state.queue_write(
            field_path=field,
            proposed_value=decision.raw_text,
            source=decision.source,
            reason=decision.reason,
            confidence=decision.confidence,
            actor=decision.actor,
            evidence=decision.evidence_span,
            session_id="ingest_pipeline",
        )
        decision.policy_result = result.get("message", str(result))
        status = result.get("status", "unknown")

        if status == "queued":
            decision.final_disposition = "queued"
        elif status == "ok":
            decision.final_disposition = "accepted"
        elif status == "blocked":
            decision.final_disposition = "blocked"
        else:
            decision.final_disposition = f"unknown:{status}"

    except Exception as e:
        decision.policy_result = f"promotion error: {e}"
        decision.final_disposition = "error"

    return decision


# ---------------------------------------------------------------------------
# Full pipeline: process one item
# ---------------------------------------------------------------------------

def process(
    text: str,
    source: str,
    actor: str = "unknown",
    dry_run: bool = False,
) -> IngestDecision:
    """
    Run the full three-stage pipeline for one input item.
    Returns a fully populated IngestDecision.
    """
    item_id = hashlib.md5(f"{text}{source}{actor}".encode()).hexdigest()[:8]
    ts = datetime.now(timezone.utc).isoformat()

    # Stage 1: memory-worthy?
    worthy, worthy_reason = is_memory_worthy(text, source)

    if worthy == "no":
        d = IngestDecision(
            item_id=item_id,
            timestamp=ts,
            source=source,
            actor=actor,
            raw_text=text,
            memory_worthy="no",
            classification=CLASS_NOISE,
            destination=DEST_DROP,
            confidence=0.95,
            promotion_eligibility="n/a",
            reason=worthy_reason,
            evidence_span="",
            final_disposition="dropped",
            dry_run=dry_run,
        )
        _append_ingest_log(d)
        return d

    # Stage 2: classify + route
    classification, confidence, class_reason, evidence = classify(text, source)
    destination, promotion_eligibility = route(classification, source)

    # If 'maybe' from Stage 1, downgrade confidence and force queue on Core State routes
    if worthy == "maybe":
        confidence = min(confidence, 0.65)
        if promotion_eligibility == "immediate":
            promotion_eligibility = "queue"

    # Suggest field for Core State candidates
    suggested = None
    if classification in CORE_STATE_CLASSES:
        suggested = suggest_field(text)
        if not suggested:
            # Can't identify field → demote to wiki for human review
            destination = DEST_WIKI
            promotion_eligibility = "n/a"
            class_reason += " (no field identified — routed to wiki for review)"

    d = IngestDecision(
        item_id=item_id,
        timestamp=ts,
        source=source,
        actor=actor,
        raw_text=text,
        memory_worthy=worthy,
        classification=classification,
        destination=destination,
        confidence=confidence,
        promotion_eligibility=promotion_eligibility,
        reason=class_reason,
        evidence_span=evidence,
        suggested_field=suggested,
        dry_run=dry_run,
    )

    # Stage 3: attempt promotion if Core State
    d = attempt_promotion(d)

    # Log everything
    _append_ingest_log(d)
    return d


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _append_ingest_log(d: IngestDecision):
    """Append decision to ingest-log.jsonl (append-only, never deleted)."""
    INGEST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INGEST_LOG_PATH, "a") as f:
        f.write(json.dumps(asdict(d)) + "\n")


def _append_ingest_queue(d: IngestDecision):
    """Append a needs-review decision to ingest-queue.jsonl."""
    INGEST_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INGEST_QUEUE_PATH, "a") as f:
        f.write(json.dumps(asdict(d)) + "\n")


def get_queue(status_filter: str = "queued_for_review") -> list[dict]:
    """Return items in the ingest queue."""
    if not INGEST_QUEUE_PATH.exists():
        return []
    items = []
    with open(INGEST_QUEUE_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if status_filter == "all" or item.get("final_disposition") == status_filter:
                    items.append(item)
            except json.JSONDecodeError:
                pass
    return items


# ---------------------------------------------------------------------------
# Golden test set — 30 examples covering the full routing surface
# ---------------------------------------------------------------------------

GOLDEN_TESTS = [
    # (text, source, expected_class, expected_destination, label)

    # --- Canonical facts (should route to Core State, queued) ---
    ("My price is now $997 for IRIS Pro.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "pricing update explicit"),

    ("The business is called IRIS.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "business name explicit"),

    ("My name is Alex.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "name explicit"),

    ("My goal is to get 10 paying users this month.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "primary goal explicit"),

    ("I sell to non-technical solopreneurs who want accountability.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "target audience explicit"),

    # --- Preferences (Core State, queued) ---
    ("Never use hype language or exclamation points.", "user_explicit",
     CLASS_PREFERENCE, DEST_CORE_STATE, "tone avoid explicit"),

    ("My writing voice is calm, direct, and confident.", "user_explicit",
     CLASS_PREFERENCE, DEST_CORE_STATE, "voice preference explicit"),

    ("Don't ever use bullet points in emails to me.", "user_explicit",
     CLASS_PREFERENCE, DEST_CORE_STATE, "format preference explicit"),

    # --- Current state / commitments ---
    ("I promised to send the contract by Friday.", "user_explicit",
     CLASS_CURRENT_STATE, DEST_CORE_STATE, "commitment explicit"),

    ("I need to do the VPS hardening before launch.", "user_explicit",
     CLASS_CURRENT_STATE, DEST_CORE_STATE, "commitment task"),

    # --- Project context ---
    ("Right now I'm working on the memory architecture for IRIS.", "user_explicit",
     CLASS_PROJECT_CTX, DEST_CORE_STATE, "project context explicit"),

    ("The current project is IRIS Pro memory scaling.", "user_explicit",
     CLASS_PROJECT_CTX, DEST_CORE_STATE, "project name explicit"),

    # --- Reference knowledge (wiki) ---
    ("The reason we're using Pinecone is that each user gets their own free API key.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "architectural rationale"),

    ("The strategy is to ship Phase 3 before adding new integrations.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "strategy note"),

    ("The plan is conservative routing first, only escalate high-signal items.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "plan note"),

    # --- Retrieval only (articles, external content) ---
    ("Here's a link to an article about Karpathy's memory approach.", "external",
     CLASS_RETRIEVAL_ONLY, DEST_RETRIEVAL, "external article link"),

    ("Meeting notes from the strategy call: discussed pricing, launch date.", "system_inferred",
     CLASS_RETRIEVAL_ONLY, DEST_RETRIEVAL, "meeting notes inferred"),

    ("According to research, solopreneurs need accountability more than tools.", "external",
     CLASS_RETRIEVAL_ONLY, DEST_RETRIEVAL, "external research claim"),

    # --- Inferred facts — should NOT reach Core State ---
    ("My price is now $997 for IRIS Pro.", "system_inferred",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "pricing inferred — should block"),
     # Note: classification may still be canonical_fact, but promotion_eligibility must be 'block'

    # "She seems to prefer" — third-person + no memory signal → Stage 1 drops before classify.
    # Dropping early is stricter than blocking; both prevent Core State writes. Accept CLASS_NOISE.
    ("She seems to prefer a casual tone based on her messages.", "system_inferred",
     CLASS_NOISE, DEST_DROP, "preference inferred — dropped in Stage 1 (stricter than block)"),

    # --- Noise — should be dropped ---
    ("ok", "user_explicit",
     CLASS_NOISE, DEST_DROP, "pure acknowledgement"),

    ("testing", "user_explicit",
     CLASS_NOISE, DEST_DROP, "test string"),

    ("lol", "user_explicit",
     CLASS_NOISE, DEST_DROP, "reaction filler"),

    ("Sure sounds good!", "user_explicit",
     CLASS_NOISE, DEST_DROP, "social filler"),

    ("hi", "user_explicit",
     CLASS_NOISE, DEST_DROP, "greeting noise"),

    # --- Ambiguous / 'maybe' cases ---
    ("I've been thinking about maybe pivoting to enterprise.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "speculative thought — not a goal yet"),

    ("Not sure yet but probably $1200 for the enterprise tier.", "user_explicit",
     CLASS_CANONICAL_FACT, DEST_CORE_STATE, "tentative pricing — should queue not write"),

    ("I'm frustrated with how long testing is taking.", "user_explicit",
     CLASS_NOISE, DEST_DROP, "transient emotion no lasting fact"),

    ("I talked to a customer who said they'd pay $500.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "third-party report — not user belief"),

    ("The approach that works best for my audience is short daily check-ins.", "user_explicit",
     CLASS_REF_KNOWLEDGE, DEST_WIKI, "strategy insight — wiki not Core State"),
]


def run_tests(verbose: bool = False) -> dict:
    """
    Run golden test set. Returns {passed, failed, total, failures}.
    Tests two things:
      1. classification matches expected_class
      2. destination matches expected_destination
    For inferred sources, also checks promotion_eligibility == 'block'.
    """
    passed = 0
    failed = 0
    failures = []

    for text, source, exp_class, exp_dest, label in GOLDEN_TESTS:
        decision = process(text, source, actor="test_suite", dry_run=True)
        ok = True
        notes = []

        if decision.classification != exp_class:
            ok = False
            notes.append(f"class: got '{decision.classification}', want '{exp_class}'")

        if decision.destination != exp_dest:
            ok = False
            notes.append(f"dest: got '{decision.destination}', want '{exp_dest}'")

        # For inferred sources targeting Core State, check block
        if source == "system_inferred" and exp_dest == DEST_CORE_STATE:
            if decision.promotion_eligibility != "block":
                ok = False
                notes.append(f"inferred must be blocked, got '{decision.promotion_eligibility}'")

        if ok:
            passed += 1
            if verbose:
                print(f"  ✓ {label}")
        else:
            failed += 1
            failures.append({"label": label, "text": text[:60], "notes": notes, "decision": asdict(decision)})
            if verbose:
                print(f"  ✗ {label}: {', '.join(notes)}")

    return {"passed": passed, "failed": failed, "total": len(GOLDEN_TESTS), "failures": failures}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IRIS Ingest Pipeline — classify and route input")
    parser.add_argument("--text", help="Text to ingest")
    parser.add_argument("--source", default="user_explicit",
                        choices=["user_explicit", "user_confirmed", "system_inferred",
                                 "system_canonical", "external"],
                        help="Source/trust class of this input")
    parser.add_argument("--actor", default="unknown", help="Who/what produced this input")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify and route but do not write anything")
    parser.add_argument("--pending", action="store_true",
                        help="Show items in the ingest review queue")
    parser.add_argument("--test", action="store_true",
                        help="Run golden test set")
    parser.add_argument("--verbose", action="store_true", help="Verbose test output")
    args = parser.parse_args()

    if args.test:
        print("Running golden test set...\n")
        results = run_tests(verbose=True)
        print(f"\n{'─'*40}")
        print(f"  {results['passed']}/{results['total']} passed", end="")
        if results["failed"]:
            print(f"  ({results['failed']} failed)")
            for f in results["failures"]:
                print(f"\n  ✗ {f['label']}")
                for note in f["notes"]:
                    print(f"      {note}")
        else:
            print("  — all green")
        sys.exit(0 if results["failed"] == 0 else 1)

    if args.pending:
        queue = get_queue(status_filter="all")
        if not queue:
            print("No items in ingest queue.")
        else:
            print(f"{len(queue)} item(s) in ingest queue:\n")
            for item in queue:
                print(f"  [{item['item_id']}] {item['classification']} → {item['destination']}")
                print(f"    \"{item['raw_text'][:80]}\"")
                print(f"    reason: {item['reason']}")
                print(f"    disposition: {item['final_disposition']}")
                print()
        sys.exit(0)

    if not args.text:
        parser.print_help()
        sys.exit(1)

    decision = process(
        text=args.text,
        source=args.source,
        actor=args.actor,
        dry_run=args.dry_run,
    )

    # Pretty output
    worthy_icon = {"yes": "✓", "maybe": "~", "no": "✗"}.get(decision.memory_worthy, "?")
    dest_icon = {DEST_CORE_STATE: "🔒", DEST_WIKI: "📄", DEST_RETRIEVAL: "🔍", DEST_DROP: "🗑"}.get(
        decision.destination, "?"
    )

    print(f"\n[{decision.item_id}] Ingest decision")
    print(f"  Memory worthy : {worthy_icon} {decision.memory_worthy}")
    print(f"  Classification: {decision.classification}")
    print(f"  Destination   : {dest_icon} {decision.destination}")
    print(f"  Confidence    : {decision.confidence:.2f}")
    print(f"  Eligibility   : {decision.promotion_eligibility}")
    print(f"  Reason        : {decision.reason}")
    if decision.evidence_span:
        print(f"  Evidence      : \"{decision.evidence_span}\"")
    if decision.suggested_field:
        print(f"  Field path    : {decision.suggested_field}")
    if decision.policy_result:
        print(f"  Policy result : {decision.policy_result}")
    if decision.final_disposition:
        print(f"  Disposition   : {decision.final_disposition}")
    if args.dry_run:
        print(f"  [dry-run — nothing written]")


if __name__ == "__main__":
    main()
