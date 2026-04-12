#!/usr/bin/env python3
"""
Script: Core State Manager
Purpose: Deterministic read/write for IRIS Core State (Layer 1 memory).
         Phase 1: Schema enforcement, write rules, audit logging.
         Phase 2: Field-level policies, gate ordering, pending review queue,
                  staleness checking, disposition logging, projection rebuild.

Gate order on every write (Phase 2):
    1. Is source recognized and not blocked?
    2. Is source allowed for this specific field? (field-policies.json)
    3. Does this field require confirmation for this write? (confirmation_policy)
    4. Does confidence meet the field's minimum threshold?
    5. Execute write, log disposition.

Usage:
    python core_state.py --get
    python core_state.py --lookup "offer_stack"
    python core_state.py --lookup "current_goals.primary"
    python core_state.py --write "offer_stack.products.0.price" "\\$997" \\
        --source user_explicit --trigger "User said price is now 997" --confidence 1.0
    python core_state.py --propose "current_goals.primary" "New goal" \\
        --source system_canonical --reason "Repeated 3x" --confidence 0.75
    python core_state.py --pending               # Show pending review queue
    python core_state.py --resolve <id> approve  # Approve a pending write
    python core_state.py --resolve <id> reject   # Reject a pending write
    python core_state.py --active-project
    python core_state.py --matches "what is my pricing"
    python core_state.py --validate
    python core_state.py --project               # Rebuild MEMORY.md from Core State
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_STATE_PATH = REPO_ROOT / "memory" / "core-state.json"
AUDIT_LOG_PATH = REPO_ROOT / "memory" / "audit-log.jsonl"
FIELD_POLICIES_PATH = REPO_ROOT / "memory" / "field-policies.json"
PENDING_WRITES_PATH = REPO_ROOT / "memory" / "pending-writes.jsonl"
MEMORY_MD_PATH = REPO_ROOT / "memory" / "MEMORY.md"

# Write dispositions logged to audit
DISPOSITION_ACCEPTED = "accepted"
DISPOSITION_REJECTED = "rejected"
DISPOSITION_BLOCKED_BY_POLICY = "blocked_by_policy"
DISPOSITION_QUEUED = "queued_for_confirmation"
DISPOSITION_STALE_FLAG = "stale_flag_triggered"

# ---------------------------------------------------------------------------
# Write rule enforcement
# ---------------------------------------------------------------------------

ALLOWED_SOURCES = {"user_explicit", "user_confirmed", "system_canonical"}

BLOCKED_SOURCES = {
    "system_inferred": "Inferred summaries cannot write to Core State. Promote to wiki instead.",
    "similarity_match": "Retrieval results cannot write to Core State.",
    "raw_import": "Raw imports cannot write to Core State. Classify first.",
    "external": "External content cannot write to Core State.",
}

# Core State fields that should NEVER be overwritten by anything other than
# user_explicit or user_confirmed (even system_canonical must be cautious here)
HIGH_PROTECTION_FIELDS = {
    "offer_stack",
    "current_goals",
    "active_commitments",
    "tone_preferences",
}


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _append_audit(action: str, layer: str, field: str, old_value, new_value,
                  source: str, trigger: str, session_id: str = None,
                  disposition: str = DISPOSITION_ACCEPTED,
                  confidence: float = 1.0, actor: str = None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "layer": layer,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "source": source,
        "trigger": trigger,
        "session_id": session_id or "unknown",
        "disposition": disposition,
        "confidence": round(confidence, 4),
        "actor": actor or "core_state_cli",
    }
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


# ---------------------------------------------------------------------------
# Field policy resolution (Phase 2)
# ---------------------------------------------------------------------------

_POLICY_CACHE: dict = {}


def _load_field_policies() -> dict:
    global _POLICY_CACHE
    if _POLICY_CACHE:
        return _POLICY_CACHE
    if not FIELD_POLICIES_PATH.exists():
        return {}
    with open(FIELD_POLICIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Remove metadata keys
    _POLICY_CACHE = {k: v for k, v in data.items() if not k.startswith("_")}
    return _POLICY_CACHE


def _get_field_policy(field_path: str) -> dict:
    """
    Return the most specific policy for a field path.
    Uses prefix matching: checks exact path, then each parent, then _default.
    """
    policies = _load_field_policies()
    default = {
        "allowed_sources": list(ALLOWED_SOURCES),
        "overwrite_behavior": "replace",
        "confirmation_policy": "on_change",
        "staleness_days": 90,
        "confidence_minimum": 0.7,
    }

    # Try exact match first, then progressively shorter prefixes
    parts = field_path.split(".")
    for length in range(len(parts), 0, -1):
        prefix = ".".join(parts[:length])
        if prefix in policies:
            policy = dict(default)
            policy.update(policies[prefix])
            return policy

    return policies.get("_default", default)


def _requires_confirmation(policy: dict, source: str, current_value) -> bool:
    """
    Determine whether this write requires user confirmation before proceeding.
    Returns True if the write should be queued, False if it can proceed.
    """
    cp = policy.get("confirmation_policy", "on_change")

    if cp == "never":
        return False
    if cp == "always":
        return True
    if cp == "always_if_non_explicit":
        return source != "user_explicit"
    if cp == "on_change":
        # Require confirmation only if a non-null value already exists
        return current_value is not None

    return False  # Unknown policy — allow by default


def check_staleness(field_path: str, policy: dict = None) -> dict | None:
    """
    Check whether a Core State field has gone stale.
    Returns a staleness dict if stale, None if fresh or no expiry.
    """
    if policy is None:
        policy = _get_field_policy(field_path)

    staleness_days = policy.get("staleness_days")
    if staleness_days is None:
        return None  # Field never expires

    state = load()
    meta = state.get("_meta", {})
    confirmed_str = meta.get("last_confirmed_at", "")
    if not confirmed_str:
        return None

    try:
        confirmed = datetime.fromisoformat(confirmed_str)
        if confirmed.tzinfo is None:
            confirmed = confirmed.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - confirmed).days
        if age_days > staleness_days:
            return {
                "stale": True,
                "field": field_path,
                "age_days": age_days,
                "staleness_threshold_days": staleness_days,
                "last_confirmed_at": confirmed_str,
                "message": (
                    f"[stale — last confirmed {age_days} days ago, "
                    f"threshold is {staleness_days} days]"
                ),
            }
    except (ValueError, TypeError):
        pass

    return None


# ---------------------------------------------------------------------------
# Pending write queue (Phase 2)
# ---------------------------------------------------------------------------

def queue_write(field_path: str, proposed_value, source: str,
                reason: str, confidence: float, actor: str = None,
                evidence: str = None, session_id: str = None) -> dict:
    """
    Add a proposed Core State write to the pending review queue.
    Used when a write is blocked by confirmation policy or confidence threshold.

    Returns the queued entry dict.
    """
    current_value = lookup(field_path)
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "field": field_path,
        "proposed_value": proposed_value,
        "current_value": current_value,
        "source": source,
        "evidence": evidence or "",
        "reason": reason,
        "confidence": round(confidence, 4),
        "actor": actor or "unknown",
        "overwrite_type": "replace" if current_value is not None else "new",
        "status": "pending",
        "resolved_at": None,
        "resolution_note": None,
        "session_id": session_id or "unknown",
    }

    PENDING_WRITES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_WRITES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")

    _append_audit(
        action="queue",
        layer="pending_writes",
        field=field_path,
        old_value=current_value,
        new_value=proposed_value,
        source=source,
        trigger=reason,
        session_id=session_id,
        disposition=DISPOSITION_QUEUED,
        confidence=confidence,
        actor=actor,
    )

    return entry


def get_pending_writes(status: str = "pending") -> list:
    """
    Return pending write entries filtered by status.
    status: "pending" | "approved" | "rejected" | "all"
    """
    if not PENDING_WRITES_PATH.exists():
        return []

    entries = []
    with open(PENDING_WRITES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if status == "all" or entry.get("status") == status:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def resolve_pending(write_id: str, resolution: str,
                    user_note: str = None, session_id: str = None) -> dict:
    """
    Approve or reject a pending write by ID.

    resolution: "approve" | "reject"

    If approved, executes the write with source=user_confirmed.
    If rejected, marks as rejected in the queue.
    Returns the resolution result.
    """
    if resolution not in ("approve", "reject"):
        raise ValueError(f"resolution must be 'approve' or 'reject', got '{resolution}'")

    if not PENDING_WRITES_PATH.exists():
        raise FileNotFoundError(f"No pending writes queue found")

    entries = []
    target = None
    with open(PENDING_WRITES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("id") == write_id and entry.get("status") == "pending":
                target = entry
            entries.append(entry)

    if target is None:
        raise ValueError(f"Pending write '{write_id}' not found or already resolved")

    # Update the entry
    now = datetime.now(timezone.utc).isoformat()
    target["status"] = "approved" if resolution == "approve" else "rejected"
    target["resolved_at"] = now
    target["resolution_note"] = user_note or ""

    # Rewrite queue
    with open(PENDING_WRITES_PATH, "w", encoding="utf-8") as f:
        for entry in entries:
            if entry.get("id") == write_id:
                f.write(json.dumps(target, default=str) + "\n")
            else:
                f.write(json.dumps(entry, default=str) + "\n")

    if resolution == "approve":
        # Execute the write with user_confirmed source
        result = write(
            field_path=target["field"],
            new_value=target["proposed_value"],
            source="user_confirmed",
            trigger=f"Approved pending write {write_id}: {target.get('reason', '')}",
            session_id=session_id,
            confidence=target.get("confidence", 1.0),
            actor=f"pending_approval:{target.get('actor', 'unknown')}",
            _skip_policy_check=True,  # Already reviewed; skip re-checking policy
        )
        return {"status": "approved", "write_result": result, "entry": target}
    else:
        _append_audit(
            action="reject",
            layer="pending_writes",
            field=target["field"],
            old_value=target["current_value"],
            new_value=target["proposed_value"],
            source="user_confirmed",
            trigger=f"Rejected pending write {write_id}: {user_note or 'no reason given'}",
            session_id=session_id,
            disposition=DISPOSITION_REJECTED,
            confidence=target.get("confidence", 0),
        )
        return {"status": "rejected", "entry": target}


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

SCHEMA_PATH = REPO_ROOT / "memory" / "core-state.schema.json"


def validate_core_state(state: dict = None) -> dict:
    """
    Validate Core State against core-state.schema.json.

    Returns:
        {"valid": True} on success
        {"valid": False, "errors": [...]} on failure

    Validation is intentionally lenient on format: date-time strings are
    checked for presence, not parsed, to avoid stdlib/jsonschema dependency issues.
    """
    if state is None:
        state = load()

    errors = []

    # Load schema
    if not SCHEMA_PATH.exists():
        return {"valid": False, "errors": [f"Schema file not found: {SCHEMA_PATH}"]}

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Check required top-level fields
    required = schema.get("required", [])
    for field in required:
        if field not in state:
            errors.append(f"Missing required field: '{field}'")

    # Check _meta required fields and types
    meta = state.get("_meta", {})
    meta_required = schema["properties"]["_meta"].get("required", [])
    for field in meta_required:
        if field not in meta:
            errors.append(f"Missing _meta field: '{field}'")
    if "version" in meta and not isinstance(meta["version"], int):
        errors.append(f"_meta.version must be integer, got {type(meta['version']).__name__}")
    allowed_sources = {"user_explicit", "user_confirmed", "system_canonical"}
    if "source_of_last_write" in meta and meta["source_of_last_write"] not in allowed_sources:
        errors.append(f"_meta.source_of_last_write invalid: '{meta['source_of_last_write']}'")

    # Check identity required fields are non-empty strings
    identity = state.get("identity", {})
    for field in ["name", "role", "business_name", "business_type"]:
        val = identity.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"identity.{field} must be a non-empty string")

    # Check current_goals
    goals = state.get("current_goals", {})
    if not goals.get("primary"):
        errors.append("current_goals.primary must be non-empty")
    if "horizon" in goals and goals["horizon"] not in ("short", "medium", "long"):
        errors.append(f"current_goals.horizon must be short/medium/long, got '{goals['horizon']}'")

    # Check offer_stack products
    products = state.get("offer_stack", {}).get("products", [])
    for i, product in enumerate(products):
        for field in ["name", "price", "status"]:
            if not product.get(field):
                errors.append(f"offer_stack.products[{i}].{field} must be non-empty")
        if product.get("status") not in ("active", "paused", "deprecated", None):
            errors.append(f"offer_stack.products[{i}].status invalid: '{product.get('status')}'")

    # Check active_commitments
    for i, commitment in enumerate(state.get("active_commitments", [])):
        if not commitment.get("description"):
            errors.append(f"active_commitments[{i}].description must be non-empty")
        if commitment.get("status") not in ("active", "completed", "dropped"):
            errors.append(f"active_commitments[{i}].status invalid: '{commitment.get('status')}'")

    # Check active_project_context
    project = state.get("active_project_context", {})
    if project.get("status") and project["status"] not in ("active", "paused", "completed"):
        errors.append(f"active_project_context.status invalid: '{project['status']}'")
    if "priority" in project and not isinstance(project["priority"], int):
        errors.append(f"active_project_context.priority must be integer")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True, "error_count": 0}


# ---------------------------------------------------------------------------
# Core State I/O
# ---------------------------------------------------------------------------

def load() -> dict:
    """Load and return the full Core State dict."""
    if not CORE_STATE_PATH.exists():
        raise FileNotFoundError(
            f"Core State not found at {CORE_STATE_PATH}. "
            "Run the Phase 1 setup to initialize it."
        )
    with open(CORE_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(state: dict):
    with open(CORE_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Lookup (deterministic, read-only)
# ---------------------------------------------------------------------------

def lookup(field_path: str):
    """
    Deterministic lookup by dot-path. Returns the value at that path.
    Does NOT trigger any search. Returns None if path not found.

    Examples:
        lookup("offer_stack")
        lookup("offer_stack.products")
        lookup("current_goals.primary")
        lookup("canonical_business_facts.custom.payment_processor")
    """
    state = load()
    parts = field_path.split(".")
    current = state
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if current is None:
            return None
    return current


def get_active_project() -> dict:
    """Shortcut: return the active_project_context field."""
    return lookup("active_project_context") or {}


# ---------------------------------------------------------------------------
# Query matching (for retrieval order Step 1)
# ---------------------------------------------------------------------------

# Maps query keywords to Core State field paths.
# When a query contains these keywords, Core State should be checked first.
FIELD_TRIGGERS = {
    # Pricing / offers
    "price": "offer_stack",
    "pricing": "offer_stack",
    "cost": "offer_stack",
    "offer": "offer_stack",
    "product": "offer_stack",
    "tier": "offer_stack",
    "iris pro": "offer_stack",
    "iris core": "offer_stack",
    "lemon squeezy": "offer_stack",
    "$": "offer_stack",
    "dollar": "offer_stack",
    # Goals
    "goal": "current_goals",
    "priority": "current_goals",
    "focus": "current_goals",
    "objective": "current_goals",
    "quarter": "current_goals",
    "this week": "current_goals",
    "working on": "current_goals",
    # Identity / business
    "who am i": "identity",
    "my name": "identity",
    "business": "canonical_business_facts",
    "telegram": "canonical_business_facts",
    "audience": "canonical_business_facts",
    "target": "canonical_business_facts",
    "subto": "canonical_business_facts",
    "pace morby": "canonical_business_facts",
    # Tone / style
    "tone": "tone_preferences",
    "style": "tone_preferences",
    "voice": "tone_preferences",
    "write like": "tone_preferences",
    "sound like": "tone_preferences",
    # Commitments
    "commitment": "active_commitments",
    "committed": "active_commitments",
    "deadline": "active_commitments",
    "due": "active_commitments",
    # Project context
    "project": "active_project_context",
    "phase": "active_project_context",
    "current project": "active_project_context",
}


def matches_query(query: str) -> tuple[bool, str, object]:
    """
    Check if a query directly matches a Core State field.

    Returns:
        (matched: bool, field_path: str, value: any)

    If matched, the caller should return the value directly without searching.
    """
    q = query.lower()
    for keyword, field_path in FIELD_TRIGGERS.items():
        if keyword in q:
            value = lookup(field_path)
            if value is not None:
                return True, field_path, value
    return False, "", None


# ---------------------------------------------------------------------------
# Write (enforced, audited)
# ---------------------------------------------------------------------------

def write(field_path: str, new_value, source: str, trigger: str,
          session_id: str = None, force: bool = False,
          confidence: float = 1.0, actor: str = None,
          _skip_policy_check: bool = False) -> dict:
    """
    Write a value to Core State, enforcing the Phase 2 gate order:
        1. Source recognized and not blocked?
        2. Source allowed for this field? (field-policies.json)
        3. Confirmation required for this write? → queue if yes
        4. Confidence meets field minimum?
        5. Execute write + log disposition.

    Args:
        field_path:   Dot-path to field (e.g. "offer_stack.products.0.price")
        new_value:    The new value to set
        source:       user_explicit | user_confirmed | system_canonical
        trigger:      Human-readable reason for this write
        session_id:   Optional session ID for audit trail
        force:        Skip high-protection field check (use with caution)
        confidence:   0.0–1.0 certainty score. Must meet field policy minimum.
        actor:        What triggered this (e.g. "iris_setup_skill", "user_chat")
        _skip_policy_check: Internal flag — used by resolve_pending() only.

    Returns:
        {"status": "ok", ...}           — write succeeded
        {"status": "queued", ...}       — write queued for user confirmation
        Raises ValueError               — write blocked

    Raises:
        ValueError: If source is blocked or not in field's allowed_sources.
    """
    sid = session_id or str(uuid.uuid4())[:8]
    act = actor or "core_state_cli"

    # ── Gate 1: Source recognized and not blocked ─────────────────────────
    if source in BLOCKED_SOURCES:
        _append_audit("write", "core_state", field_path, lookup(field_path), new_value,
                      source, trigger, sid, DISPOSITION_REJECTED, confidence, act)
        raise ValueError(
            f"Write blocked: source '{source}' cannot write to Core State.\n"
            f"Reason: {BLOCKED_SOURCES[source]}"
        )
    if source not in ALLOWED_SOURCES:
        _append_audit("write", "core_state", field_path, lookup(field_path), new_value,
                      source, trigger, sid, DISPOSITION_REJECTED, confidence, act)
        raise ValueError(
            f"Write blocked: source '{source}' is not recognized.\n"
            f"Allowed: {', '.join(ALLOWED_SOURCES)}"
        )

    current_value = lookup(field_path)

    if not _skip_policy_check:
        policy = _get_field_policy(field_path)

        # ── Gate 2: Source allowed for this field ─────────────────────────
        allowed = policy.get("allowed_sources", list(ALLOWED_SOURCES))
        if source not in allowed:
            _append_audit("write", "core_state", field_path, current_value, new_value,
                          source, trigger, sid, DISPOSITION_BLOCKED_BY_POLICY, confidence, act)
            raise ValueError(
                f"Write blocked by field policy: source '{source}' is not allowed "
                f"for field '{field_path}'.\nAllowed: {allowed}"
            )

        # ── Gate 3: Confirmation required? ───────────────────────────────
        if not force and _requires_confirmation(policy, source, current_value):
            queued = queue_write(
                field_path=field_path,
                proposed_value=new_value,
                source=source,
                reason=trigger,
                confidence=confidence,
                actor=act,
                session_id=sid,
            )
            return {
                "status": "queued",
                "message": (
                    f"Write to '{field_path}' requires user confirmation "
                    f"(policy: {policy.get('confirmation_policy')})."
                ),
                "queued_id": queued["id"],
                "field": field_path,
                "proposed_value": new_value,
                "current_value": current_value,
            }

        # ── Gate 4: Confidence meets minimum ─────────────────────────────
        min_conf = policy.get("confidence_minimum", 0.7)
        if confidence < min_conf:
            queued = queue_write(
                field_path=field_path,
                proposed_value=new_value,
                source=source,
                reason=f"[low confidence: {confidence:.2f} < {min_conf}] {trigger}",
                confidence=confidence,
                actor=act,
                session_id=sid,
            )
            return {
                "status": "queued",
                "message": (
                    f"Write to '{field_path}' queued: confidence {confidence:.2f} "
                    f"is below field minimum {min_conf}."
                ),
                "queued_id": queued["id"],
            }

    # ── Gate 5 (legacy): High-protection field check ──────────────────────
    top_level_field = field_path.split(".")[0]
    if not force and top_level_field in HIGH_PROTECTION_FIELDS and source == "system_canonical":
        _append_audit("write", "core_state", field_path, current_value, new_value,
                      source, trigger, sid, DISPOSITION_BLOCKED_BY_POLICY, confidence, act)
        raise ValueError(
            f"Write blocked: '{top_level_field}' is a high-protection field.\n"
            "Requires source='user_explicit' or 'user_confirmed'.\n"
            "Pass force=True to override (use with caution)."
        )

    # ── Execute write ─────────────────────────────────────────────────────
    state = load()
    parts = field_path.split(".")

    parent = state
    for part in parts[:-1]:
        if isinstance(parent, dict):
            if part not in parent:
                parent[part] = {}
            parent = parent[part]
        elif isinstance(parent, list):
            try:
                parent = parent[int(part)]
            except (ValueError, IndexError):
                raise ValueError(f"Invalid path segment '{part}' in '{field_path}'")

    final_key = parts[-1]
    if isinstance(parent, list):
        try:
            parent[int(final_key)] = new_value
        except (ValueError, IndexError):
            raise ValueError(f"Invalid list index '{final_key}' in '{field_path}'")
    elif isinstance(parent, dict):
        parent[final_key] = new_value
    else:
        raise ValueError(f"Cannot write to '{field_path}': parent is not a dict or list")

    # Update metadata
    now = datetime.now(timezone.utc).isoformat()
    state["_meta"]["version"] = state["_meta"].get("version", 0) + 1
    state["_meta"]["last_updated_at"] = now
    if source in ("user_explicit", "user_confirmed"):
        state["_meta"]["last_confirmed_at"] = now
    state["_meta"]["source_of_last_write"] = source

    _save(state)

    _append_audit(
        action="write",
        layer="core_state",
        field=field_path,
        old_value=current_value,
        new_value=new_value,
        source=source,
        trigger=trigger,
        session_id=sid,
        disposition=DISPOSITION_ACCEPTED,
        confidence=confidence,
        actor=act,
    )

    return {
        "status": "ok",
        "field": field_path,
        "old_value": current_value,
        "new_value": new_value,
        "source": source,
        "confidence": confidence,
        "actor": act,
    }


# ---------------------------------------------------------------------------
# Batch update
# ---------------------------------------------------------------------------

def update_core_state(patch: dict, source: str, trigger: str,
                      session_id: str = None) -> dict:
    """
    Apply multiple field updates in a single confirmed operation.

    Args:
        patch:      Dict of {field_path: new_value} pairs to update
        source:     Must be one of: user_explicit, user_confirmed, system_canonical
        trigger:    Human-readable description of what caused these updates
        session_id: Optional session identifier for audit trail

    Returns:
        {"status": "ok", "updated": [...], "skipped": [...], "errors": [...]}

    Each field is written individually through write() so all rules are enforced.
    If one field fails, the rest still proceed — partial updates are allowed.
    All successful writes are logged to audit-log.jsonl.
    The final state is validated against the schema before returning.
    """
    if source in BLOCKED_SOURCES:
        raise ValueError(
            f"Batch update blocked: source '{source}' cannot write to Core State.\n"
            f"Reason: {BLOCKED_SOURCES[source]}"
        )
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"Batch update blocked: unrecognized source '{source}'")

    sid = session_id or str(uuid.uuid4())[:8]
    updated = []
    skipped = []
    errors = []

    for field_path, new_value in patch.items():
        try:
            result = write(
                field_path=field_path,
                new_value=new_value,
                source=source,
                trigger=f"[batch] {trigger}",
                session_id=sid,
            )
            updated.append({"field": field_path, "old_value": result["old_value"], "new_value": new_value})
        except ValueError as e:
            errors.append({"field": field_path, "error": str(e)})
        except Exception as e:
            errors.append({"field": field_path, "error": f"Unexpected error: {e}"})

    # Validate final state
    validation = validate_core_state()
    if not validation["valid"]:
        errors.append({"field": "_schema_validation", "error": validation["errors"]})

    return {
        "status": "ok" if not errors else "partial",
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "valid_after_update": validation["valid"],
    }


# ---------------------------------------------------------------------------
# Formatted output helpers
# ---------------------------------------------------------------------------

def format_for_context(fields: list[str] = None) -> str:
    """
    Return a formatted Core State summary suitable for injecting into a prompt.
    If fields is provided, only include those top-level fields.
    """
    state = load()
    meta = state.get("_meta", {})

    lines = [
        f"[Core State v{meta.get('version', '?')} — confirmed {meta.get('last_confirmed_at', 'unknown')}]",
        "",
    ]

    sections = fields or [
        "identity", "current_goals", "offer_stack",
        "tone_preferences", "active_project_context",
        "canonical_business_facts", "active_commitments",
    ]

    for section in sections:
        if section not in state:
            continue
        lines.append(f"### {section.replace('_', ' ').title()}")
        lines.append(json.dumps(state[section], indent=2, ensure_ascii=False))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Projection rebuild (Phase 2) — deterministic MEMORY.md from Core State
# ---------------------------------------------------------------------------

def generate_projection(write_file: bool = False) -> str:
    """
    Generate a deterministic human-readable MEMORY.md from core-state.json.
    Same Core State always produces the same output.

    If write_file=True, overwrites memory/MEMORY.md.
    Always returns the generated content as a string.
    """
    state = load()
    meta = state.get("_meta", {})
    identity = state.get("identity", {})
    goals = state.get("current_goals", {})
    offers = state.get("offer_stack", {})
    tone = state.get("tone_preferences", {})
    commitments = state.get("active_commitments", [])
    project = state.get("active_project_context", {})
    business = state.get("canonical_business_facts", {})
    custom = business.get("custom", {})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    version = meta.get("version", "?")
    confirmed = meta.get("last_confirmed_at", "unknown")[:10]

    lines = [
        "# Persistent Memory",
        "",
        f"> Auto-generated from `memory/core-state.json` v{version} on {now}",
        f"> Last confirmed: {confirmed}",
        "> **Do not edit this file directly.** Update `core-state.json` via `core_state.py`, then run `--project` to rebuild.",
        "",
        "---",
        "",
        "## Identity",
        "",
        f"- **Name:** {identity.get('name', '')}",
        f"- **Role:** {identity.get('role', '')}",
        f"- **Business:** {identity.get('business_name', '')} — {identity.get('business_type', '')}",
        "",
        "## Current Goals",
        "",
        f"**Primary:** {goals.get('primary', '')}",
        "",
    ]

    secondary = goals.get("secondary", [])
    if secondary:
        lines.append("**Secondary:**")
        for goal in secondary:
            lines.append(f"- {goal}")
        lines.append("")

    horizon = goals.get("horizon", "")
    last_stated = goals.get("last_stated_at", "")[:10]
    lines.append(f"Horizon: **{horizon}** | Last stated: {last_stated}")
    lines.append("")

    lines += [
        "## Offer Stack",
        "",
        "| Product | Price | Status |",
        "|---------|-------|--------|",
    ]
    for p in offers.get("products", []):
        lines.append(f"| {p.get('name','')} | {p.get('price','')} | {p.get('status','')} |")
    pricing_confirmed = offers.get("pricing_last_confirmed_at", "")[:10]
    lines += ["", f"Pricing last confirmed: {pricing_confirmed}", ""]

    lines += [
        "## Tone Preferences",
        "",
        f"- **Style:** {tone.get('communication_style', '')}",
        f"- **Voice:** {tone.get('writing_voice', '')}",
    ]
    avoid = tone.get("avoid", [])
    if avoid:
        lines.append("- **Avoid:**")
        for item in avoid:
            lines.append(f"  - {item}")
    lines.append("")

    lines += ["## Active Project", ""]
    if project.get("project_name"):
        lines += [
            f"- **{project['project_name']}** (status: {project.get('status','')}, priority: {project.get('priority','')})",
            f"- Phase: {project.get('current_phase','')}",
            f"- Last touched: {str(project.get('last_touched_at',''))[:10]}",
        ]
    else:
        lines.append("- No active project set")
    lines.append("")

    lines += ["## Active Commitments", ""]
    active = [c for c in commitments if c.get("status") == "active"]
    if active:
        for c in active:
            due = c.get("due_date") or "no due date"
            lines.append(f"- {c['description']} (due: {str(due)[:10]})")
    else:
        lines.append("- None active")
    lines.append("")

    lines += [
        "## Business Facts",
        "",
        f"- **Audience:** {business.get('target_audience','')}",
        f"- **Platform:** {business.get('primary_platform','')}",
        f"- **Location:** {business.get('location','')}",
    ]
    for k, v in custom.items():
        if isinstance(v, list):
            lines.append(f"- **{k.replace('_',' ').title()}:** {', '.join(str(i) for i in v)}")
        else:
            lines.append(f"- **{k.replace('_',' ').title()}:** {v}")
    lines.append("")

    lines += [
        "## Learned Behaviors",
        "",
        "- Check existing skills before starting any task",
        "- Use model routing for cost efficiency (Haiku for simple, Sonnet for routine, Opus for complex)",
        "",
        "## Technical Context",
        "",
        f"- Memory: Core State (core-state.json v{version}) + daily logs + Pinecone vector search",
        f"- Telegram bot: {business.get('primary_platform', '@Heyitsirisbot')}",
        "",
        "---",
        "",
        f"*Auto-generated {now} | Core State v{version} | Last confirmed {confirmed}*",
    ]

    content = "\n".join(lines) + "\n"

    if write_file:
        MEMORY_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_MD_PATH, "w", encoding="utf-8") as f:
            f.write(content)

    return content


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="IRIS Core State manager — deterministic read/write for Layer 1 memory"
    )
    parser.add_argument("--get", action="store_true", help="Print full Core State as JSON")
    parser.add_argument("--lookup", type=str, metavar="FIELD_PATH",
                        help="Deterministic lookup by dot-path (e.g. 'offer_stack')")
    parser.add_argument("--write", nargs=2, metavar=("FIELD_PATH", "VALUE"),
                        help="Write a value to a field path")
    parser.add_argument("--source", type=str,
                        choices=["user_explicit", "user_confirmed", "system_canonical"],
                        help="Write source (required for --write)")
    parser.add_argument("--trigger", type=str, default="CLI write",
                        help="Description of what triggered this write (for audit log)")
    parser.add_argument("--session", type=str, default=None,
                        help="Session ID for audit trail")
    parser.add_argument("--active-project", action="store_true",
                        help="Print active project context")
    parser.add_argument("--matches", type=str, metavar="QUERY",
                        help="Check if a query matches Core State fields")
    parser.add_argument("--context", action="store_true",
                        help="Print formatted Core State for prompt injection")
    parser.add_argument("--validate", action="store_true",
                        help="Validate Core State against schema")
    parser.add_argument("--update", type=str, metavar="JSON_PATCH",
                        help="Batch update: JSON object of {field_path: value} pairs")
    parser.add_argument("--confidence", type=float, default=1.0,
                        help="Confidence score for --write or --update (0.0–1.0, default: 1.0)")
    parser.add_argument("--actor", type=str, default=None,
                        help="Actor label for audit trail (e.g. iris_setup_skill, user_chat)")
    parser.add_argument("--propose", nargs=2, metavar=("FIELD_PATH", "VALUE"),
                        help="Queue a proposed write for review (does not write to Core State)")
    parser.add_argument("--reason", type=str, default="Proposed update",
                        help="Reason for --propose (shown in review queue)")
    parser.add_argument("--evidence", type=str, default=None,
                        help="Evidence/excerpt supporting --propose")
    parser.add_argument("--pending", action="store_true",
                        help="Show all pending writes awaiting review")
    parser.add_argument("--resolve", nargs=2, metavar=("WRITE_ID", "DECISION"),
                        help="Resolve a pending write: --resolve <id> approve|reject")
    parser.add_argument("--project", action="store_true",
                        help="Rebuild MEMORY.md from Core State (deterministic projection)")
    args = parser.parse_args()

    if args.get:
        print(json.dumps(load(), indent=2, ensure_ascii=False))

    elif args.lookup:
        result = lookup(args.lookup)
        if result is None:
            print(f"Field '{args.lookup}' not found in Core State.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.write:
        if not args.source:
            print("Error: --source is required for --write", file=sys.stderr)
            sys.exit(1)
        field_path, raw_value = args.write
        # Try to parse JSON value; fall back to string
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        try:
            result = write(
                field_path=field_path,
                new_value=value,
                source=args.source,
                trigger=args.trigger,
                session_id=args.session,
                confidence=args.confidence,
                actor=args.actor,
            )
            print(json.dumps(result, indent=2, default=str))
        except ValueError as e:
            print(f"✗ {e}", file=sys.stderr)
            sys.exit(1)

    elif args.active_project:
        print(json.dumps(get_active_project(), indent=2, ensure_ascii=False))

    elif args.matches:
        matched, field, value = matches_query(args.matches)
        if matched:
            print(f"✓ Core State match — field: {field}")
            print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
        else:
            print("✗ No Core State match — proceed to wiki/vector search")

    elif args.validate:
        result = validate_core_state()
        if result["valid"]:
            print("✓ Core State is valid")
        else:
            print(f"✗ Core State validation failed — {len(result['errors'])} error(s):")
            for err in result["errors"]:
                print(f"  • {err}")
            sys.exit(1)

    elif args.update:
        if not args.source:
            print("Error: --source is required for --update", file=sys.stderr)
            sys.exit(1)
        try:
            patch = json.loads(args.update)
        except json.JSONDecodeError as e:
            print(f"Error: --update value must be valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        result = update_core_state(
            patch=patch,
            source=args.source,
            trigger=args.trigger,
            session_id=args.session,
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.propose:
        if not args.source:
            print("Error: --source is required for --propose", file=sys.stderr)
            sys.exit(1)
        field_path, raw_value = args.propose
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        result = queue_write(
            field_path=field_path,
            proposed_value=value,
            source=args.source,
            reason=args.reason,
            confidence=args.confidence,
            actor=args.actor,
            evidence=args.evidence,
            session_id=args.session,
        )
        print(f"✓ Queued write {result['id']} for field '{field_path}'")
        print(json.dumps(result, indent=2, default=str))

    elif args.pending:
        entries = get_pending_writes(status="pending")
        if not entries:
            print("✓ No pending writes.")
        else:
            print(f"⏳ {len(entries)} pending write(s):\n")
            for e in entries:
                print(f"  [{e['id']}] {e['field']}")
                print(f"    Current:  {json.dumps(e['current_value'], default=str)}")
                print(f"    Proposed: {json.dumps(e['proposed_value'], default=str)}")
                print(f"    Source: {e['source']} | Confidence: {e['confidence']} | Actor: {e['actor']}")
                print(f"    Reason: {e['reason']}")
                if e.get("evidence"):
                    print(f"    Evidence: {e['evidence'][:120]}...")
                print()

    elif args.resolve:
        write_id, decision = args.resolve
        if decision not in ("approve", "reject"):
            print("Error: decision must be 'approve' or 'reject'", file=sys.stderr)
            sys.exit(1)
        result = resolve_pending(
            write_id=write_id,
            resolution=decision,
            user_note=args.trigger if args.trigger != "CLI write" else None,
            session_id=args.session,
        )
        status = result["status"]
        print(f"{'✓' if status == 'approved' else '✗'} Write {write_id} {status}")
        print(json.dumps(result, indent=2, default=str))

    elif args.project:
        content = generate_projection(write_file=True)
        print(f"✓ MEMORY.md rebuilt from Core State v{load()['_meta']['version']}")
        print(f"  Written to: {MEMORY_MD_PATH}")
        print()
        print(content[:500] + ("..." if len(content) > 500 else ""))

    elif args.context:
        print(format_for_context())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
