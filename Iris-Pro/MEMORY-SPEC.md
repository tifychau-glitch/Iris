# IRIS Memory System Specification

> Version: 1.0  
> Status: Approved for implementation  
> Last updated: 2026-04-12  
> Authors: Tiffany Chau + Claude Code (synthesized from Karpathy thread research, ChatGPT review, architectural iteration)

---

## 1. Principles

### What this system is for
- Reliable, personalized context that persists across sessions
- Deterministic lookup for canonical facts (pricing, goals, commitments)
- Retrieval support for broader knowledge and context
- Transparent deprecation of old or conflicting information

### What this system is NOT for
- Silent mutation of high-trust facts
- Treating AI inferences as confirmed user beliefs
- Indexing everything — most content should not live in long-term memory
- Auto-resolving contradictions without user input

### The one rule that prevents the most damage
> **IRIS flags contradictions. IRIS does not resolve them in Core State. The user resolves them.**  
> The system may auto-resolve only for predefined canonical actions the user approved by design (e.g. a goal update from the iris-setup wizard).

---

## 2. Memory Layers

Three layers. Each has a distinct role. They are not peers — they have a strict trust hierarchy.

```
Layer 1: Core State          ← highest trust, deterministic lookup
Layer 2: Curated Wiki        ← medium-high trust, LLM-assisted synthesis
Layer 3: Retrieval Index     ← search layer only, never source of truth
```

### Layer 1 — Core State
- Structured, deterministic, machine-readable
- Holds canonical facts: identity, goals, pricing, preferences, commitments
- Queried first, always, before any search
- **Never modified by inference, similarity match, or raw import**
- Human-readable but not narrative — it is a profile record, not a document
- Storage: `memory/core-state.json` (versioned, append-only audit log)

### Layer 2 — Curated Wiki
- Organized markdown files in `memory/wiki/` (Obsidian-compatible)
- LLM-assisted synthesis from ingested content
- Contradiction-flagged by LLM, resolved by user
- Linked pages (concepts, projects, decisions, people)
- MCPVault-accessible so Claude can read/write natively
- Source of truth for nuanced, contextual knowledge
- Storage: `memory/wiki/**/*.md` with YAML frontmatter

### Layer 3 — Retrieval Index
- Pinecone (vector / semantic search) + BM25 (keyword search)
- Indexes selected, curated content — not raw imports or messy notes
- Used only when Layers 1 and 2 don't fully answer a query
- **Not a truth layer.** Retrieval results are candidates, ranked by trust + freshness
- Each user provides their own Pinecone API key (free tier)

---

## 3. Schemas

### 3a. Ingest Item Schema

Every piece of incoming content gets this envelope before routing.

```json
{
  "id": "uuid-v4",
  "source_type": "conversation | article | note | decision | document | system",
  "content_type": "fact | preference | goal | commitment | context | reference | raw",
  "author_type": "user_explicit | user_confirmed | system_inferred | system_canonical | external",
  "created_at": "ISO 8601",
  "ingested_at": "ISO 8601",
  "trust_class": "core | curated | indexed | archived",
  "promotion_status": "raw | classified | promoted | archived | rejected",
  "canonical_entity": "string or null",
  "summary": "LLM-generated one-paragraph summary",
  "raw_content": "original text, truncated if >10K tokens",
  "tags": ["list", "of", "strings"],
  "needs_review": true,
  "expires_at": "ISO 8601 or null",
  "confidence": 0.0,
  "overwrites_id": "uuid or null"
}
```

**Field notes:**
- `author_type` is the most important field for trust routing. `user_explicit` is highest trust. `system_inferred` never reaches Core State.
- `canonical_entity` links this item to a named entity in Core State (e.g. "IRIS pricing", "Mount Everest goal")
- `overwrites_id` chains supersession — if this item replaces an older one, link it here
- `needs_review` defaults to `true` for anything not from `system_canonical`. IRIS surfaces these periodically.
- `confidence` is derived, not arbitrary: see Section 7 (retrieval ranking)

---

### 3b. Core State Schema

Tight, boring, explicit. That is the point.

```json
{
  "_meta": {
    "version": 0,
    "last_updated_at": "ISO 8601",
    "last_confirmed_at": "ISO 8601",
    "source_of_last_write": "user_explicit | system_canonical",
    "audit_log_ref": "path/to/audit-entry"
  },
  "identity": {
    "name": "",
    "role": "",
    "business_name": "",
    "business_type": ""
  },
  "current_goals": {
    "primary": "",
    "secondary": [],
    "horizon": "short | medium | long",
    "last_stated_at": "ISO 8601"
  },
  "offer_stack": {
    "products": [
      {
        "name": "",
        "price": "",
        "description": "",
        "status": "active | paused | deprecated"
      }
    ],
    "pricing_last_confirmed_at": "ISO 8601"
  },
  "tone_preferences": {
    "communication_style": "",
    "writing_voice": "",
    "avoid": []
  },
  "active_commitments": [
    {
      "description": "",
      "due_date": "ISO 8601 or null",
      "status": "active | completed | dropped"
    }
  ],
  "active_project_context": {
    "project_name": "",
    "status": "active | paused | completed",
    "priority": 1,
    "current_phase": "",
    "last_touched_at": "ISO 8601"
  },
  "canonical_business_facts": {
    "target_audience": "",
    "primary_platform": "",
    "location": "",
    "custom": {}
  }
}
```

**Design notes:**
- `_meta.version` increments on every write. Never reset.
- `custom` in `canonical_business_facts` allows IRIS-specific fields without schema changes.
- All timestamps are ISO 8601. No relative dates in Core State.

---

### 3c. Wiki Page Frontmatter Schema

Every wiki page carries this YAML header.

```yaml
---
id: uuid-v4
title: Page Title
entity_type: concept | project | person | decision | reference | synthesis
trust_class: curated
author_type: user_explicit | system_inferred
created_at: ISO 8601
updated_at: ISO 8601
last_reviewed_at: ISO 8601 or null
confidence: 0.0–1.0
source_ids: [list of ingest item ids]
tags: []
status: active | stale | archived | contradiction_flagged
linked_pages: []
---
```

**Status rules:**
- `stale` — not updated in 90+ days, not reinforced by new content
- `contradiction_flagged` — LLM detected a conflict with another page or Core State. Requires user review before IRIS cites this page as truth.
- `archived` — removed from active retrieval but preserved for audit

---

## 4. Core State Write Rules

### Allowed writes — only these three sources may update Core State:

| Source | Example |
|--------|---------|
| **User explicit statement** | "My price is now $297" / "My main goal this quarter is X" |
| **User explicit confirmation** | IRIS proposes an update, user says "yes, update that" |
| **Canonical system action** | iris-setup wizard completes, goal-setting skill saves output |

### Disallowed writes — these never touch Core State directly:

| Blocked source | Why |
|----------------|-----|
| System inference | "Based on recent notes, goal seems to be X" → wiki only |
| Similarity match | Retrieved chunk that sounds like a goal → indexed content only |
| Raw import | Article or note ingested without classification → needs review first |
| Unconfirmed contradiction resolution | LLM detects conflict → flags it, does NOT auto-fix |
| Conversational guess | AI assumes something from context → never promoted without confirmation |

### Write process for Core State:
1. Trigger: user statement OR user confirmation OR canonical action
2. IRIS drafts the update and shows it to the user explicitly
3. User confirms ("yes") or modifies
4. Update written with `source_of_last_write`, `last_confirmed_at`, audit log entry
5. Old value preserved in audit log (never deleted)

---

## 5. Classification and Routing Rules

When an item is ingested, it is classified and routed to one or more layers.

| Content Type | Default Route | Can Promote to Core? | Needs Review? | Expires? |
|---|---|---|---|---|
| **conversation** | Extract durable facts → wiki | Only after user confirmation | Yes | No |
| **decision** | wiki + candidate for Core | Yes, after confirmation | Yes | No |
| **article / external content** | Summarize → indexed | Never (not user belief) | Yes | After 180 days |
| **note (raw)** | Hold in review queue | No | Yes | No |
| **note (curated)** | wiki | Only after confirmation | Yes | No |
| **note (actionable)** | wiki + commitment field | If commitment, yes | Yes | When completed |
| **system canonical action** | Core State directly | Yes, by design | No | No |
| **preference stated** | Core State (with confirmation) | Yes | No | No |

**Key rule:** Articles and external content are never treated as user beliefs. They are reference material. Pinecone may index them, but they cannot update Core State or be cited as "what the user thinks."

---

## 6. Conflict and Contradiction Policy

### Precedence hierarchy (higher overrides lower):

```
1. Core State (explicit, confirmed)
2. Curated Wiki (user-authored or explicitly confirmed)
3. Retrieval Index results (semantic/keyword matches)
4. System inference
```

### Within the same trust class:
- Explicit user-stated > system-inferred
- Confirmed > unconfirmed  
- Newer confirmed > older confirmed (with audit trail preserved)

### What happens when a contradiction is detected:

1. **LLM flags it** — surfaces the conflict with both versions, asks user which is correct
2. **User resolves it** — user picks the correct version or provides a new one
3. **System updates** — winning version promoted, losing version archived with note
4. **Audit entry created** — what was overwritten, when, why, who decided

**IRIS never silently overwrites.** If a conflict exists and the user is not available to resolve it, IRIS uses the higher-trust layer and appends a `[!contradiction]` callout to the wiki page.

---

## 7. Retrieval Policy

### Retrieval order (deterministic — run in sequence, stop when sufficient)

1. **Core State lookup** — deterministic, always first. If query matches a Core State field, return it directly. Do not search.
2. **Active project context lookup** — check `active_project_context` in Core State. Inject as context for the query.
3. **Curated wiki search** — BM25 keyword search across `memory/wiki/`. Read matched pages.
4. **Link expansion** — only if relevance score ≥ 0.7, follow one level of wiki links to adjacent pages.
5. **Pinecone vector search** — semantic search over indexed content. Returns candidates only.
6. **Rank and return** — apply scoring formula, return answer with source labels and confidence.

### Retrieval ranking formula

```
final_score = trust_weight × freshness_weight × relevance_score × source_bonus
```

**trust_weight** (from source layer and author type):
```
Core State, user_explicit:    1.00
Core State, system_canonical: 0.95
Wiki, user_explicit:          0.90
Wiki, user_confirmed:         0.85
Wiki, system_inferred:        0.65
Indexed, external:            0.50
Indexed, system_inferred:     0.40
```

**freshness_weight** (exponential decay):
```
Core State:               1.00 (no decay — confirmed facts don't expire)
Wiki pages (active):      e^(-0.023 × age_days)  [half-life ≈ 30 days]
Wiki pages (stale):       0.30 cap
Indexed content:          e^(-0.023 × age_days)  [same decay, lower floor]
```

**relevance_score**: normalized 0–1 from retrieval (BM25 score or Pinecone cosine similarity)

**source_bonus**:
```
+0.15  canonical_entity matches query entity exactly
+0.10  item tagged as stable_fact
+0.05  item has been reinforced (cited or confirmed) 2+ times
-0.10  item status is stale or contradiction_flagged
```

**Confidence shown to user** is derived from `final_score`, not from model vibes:
- `final_score ≥ 0.85` → "High confidence"
- `final_score 0.65–0.84` → "Based on [source], though this may be outdated"
- `final_score < 0.65` → "Uncertain — you may want to verify this"

---

## 8. Pruning and Promotion Loop

Runs weekly (or on-demand via `/memory lint`).

### Stale detection
- Wiki pages not updated in 90+ days → status set to `stale`
- Indexed chunks not accessed in 180+ days → demoted to `archived`
- Core State fields with `last_confirmed_at` > 180 days → flagged for re-confirmation

### Duplicate detection
- Items with cosine similarity ≥ 0.95 → flagged for merge review
- Merge requires user confirmation; IRIS proposes which to keep

### Promotion triggers (item → Core State candidate)
- Item confirmed by user 2+ times across different sessions
- Item tagged as `decision` with user confirmation
- Item sourced from canonical system action (e.g. iris-setup)
- Promotion always requires explicit user confirmation before Core State write

### Archive rules
- `stale` wiki pages not reviewed within 30 days of being flagged → `archived`
- `archived` items preserved in `memory/archive/` — never deleted
- `archived` items excluded from retrieval but available for manual review

### Human approval points (never automated)
- Any promotion to Core State
- Any contradiction resolution
- Any bulk archive operation
- Any field deletion from Core State

---

## 9. Auditability

Every write to Core State and every promoted wiki page generates an audit entry.

**Audit log location:** `memory/audit-log.jsonl` (append-only, one JSON object per line)

```json
{
  "timestamp": "ISO 8601",
  "action": "write | promote | archive | conflict_flagged | conflict_resolved",
  "layer": "core_state | wiki | index",
  "field": "field name or wiki page id",
  "old_value": "previous value or null",
  "new_value": "new value",
  "source": "user_explicit | user_confirmed | system_canonical",
  "trigger": "description of what caused the write",
  "session_id": "uuid"
}
```

This log is how you debug memory corruption. Without it, tracing why IRIS believes something wrong is nearly impossible.

---

## 10. Active Project Context — Definition

`active_project_context` is a bounded Core State field, not fuzzy inference.

```json
{
  "project_name": "string",
  "status": "active | paused | completed",
  "priority": 1,
  "current_phase": "string",
  "last_touched_at": "ISO 8601"
}
```

**Rules:**
- Only one project can be `active` at a time in Core State
- User sets this explicitly ("I'm working on X this week") or via a skill
- IRIS uses this to bias wiki search and retrieval toward relevant content
- It does not auto-update based on conversation topics — user sets it

---

## 11. Open Questions (Resolve Before Full Build)

- [ ] Should wiki pages be stored in Obsidian-compatible format from day one, or migrate later? (MCPVault integration depends on this)
- [ ] How should multi-user IRIS deployments handle separate Core States? (One JSON per user? Separate directories?)
- [ ] What is the retention policy for the audit log? (Keep forever? Rotate after 1 year?)
- [ ] Should IRIS surface the weekly pruning report to users, or run silently?
- [ ] Pinecone namespace strategy: one namespace per user, or one per content domain?

---

## 12. MVP Implementation Order

Build the risky parts first. Each phase should be independently testable.

### Phase 1 — Core State (deterministic foundation) ✅ DONE 2026-04-12
- [x] Create `memory/core-state.json` with schema from Section 3b
- [x] Write Core State reader (deterministic lookup, no search) — `core_state.py --lookup`
- [x] Write Core State writer with write rules enforced (Section 4) — `core_state.py --write`
- [x] Create `memory/audit-log.jsonl` and append on every write
- [x] Add Core State lookup as Step 1 in retrieval — `smart_search.py --tiered`
- [x] JSON Schema validation — `core-state.schema.json`, `--validate` flag
- [x] `memory-protocol.md` updated with source-of-truth hierarchy

### Phase 2 — Write Governance ✅ DONE 2026-04-12
- [x] `memory/field-policies.json` — per-field write rules (confirmation_policy enum, nullable staleness_days, confidence_minimum, overwrite_behavior)
- [x] `memory/pending-writes.jsonl` — review queue with full metadata (current_value, evidence, confidence, actor)
- [x] 5-gate write enforcement in `core_state.py` (source → field policy → confirmation → confidence → execute)
- [x] All dispositions logged to audit (accepted / rejected / blocked_by_policy / queued / stale_flag)
- [x] Deterministic MEMORY.md projection rebuild — `--project` flag
- [x] `check_staleness()` function for time-sensitive fields

### Phase 3 — Ingest Pipeline ✅ DONE 2026-04-12
Built in `.claude/skills/memory/scripts/ingest.py`. Three decisions, strictly separated:

**Stage 1 — Is this memory-worthy?** (`is_memory_worthy`)
- Verdict: `yes | maybe | no`. Default is `no`.
- `system_inferred`/`external` need an explicit memory signal to even reach Stage 2
- Transient emotion patterns drop before classification
- Noise patterns (filler, greetings, test strings) drop immediately

**Stage 2 — What type of memory?** (`classify` + `route`)
- Check order: retrieval signals → meta-observation prefixes → tentative fact signals → field signals → ref signals → fallback
- 7 routing classes: `canonical_fact | preference | current_state | project_context | reference_knowledge | retrieval_only | noise`
- Destinations: `core_state | wiki | retrieval | drop`
- Confidence grounded in source type (user_explicit → 0.88 base, system_inferred → 0.50 base)
- `suggest_field()` maps input to specific Core State field path

**Stage 3 — Write/queue/block?** (`attempt_promotion`)
- Plugs directly into Phase 2 `queue_write()` — field policies and confirmation gates apply
- `system_inferred` source → block (never writes Core State)
- `user_explicit`/`user_confirmed` → queue (on_change policy for most fields)
- `system_canonical` → can be immediate if field policy allows

**Golden test set:** 30 labeled examples embedded in `GOLDEN_TESTS`, run with `--test`. All 30 pass. Covers: explicit facts, preferences, commitments, project context, reference knowledge, retrieval-only, noise, inferred (blocked), tentative (queued low-confidence), emotional (dropped), meta-observations (wiki not Core), third-party reports (wiki not Core).

**CLI:**
```bash
python3 ingest.py --text "..." --source user_explicit --actor tiffany
python3 ingest.py --text "..." --dry-run        # classify only, no writes
python3 ingest.py --pending                     # show review queue
python3 ingest.py --test                        # run golden test set
```

**Logged to:** `memory/ingest-log.jsonl` (every decision), `memory/ingest-queue.jsonl` (review items)

### Phase 4 — Retrieval Ranking ✅ DONE 2026-04-12
Built in `.claude/skills/memory/scripts/ranking.py`, wired into `tiered_search()` in `smart_search.py`.

**Formula:** `final_score = trust_weight × freshness_modifier × relevance_score × source_bonus`

**Trust priors** (TRUST_PRIORS dict):
- Core State user_explicit: 1.00, system_canonical: 0.95
- Wiki user_explicit: 0.90, user_confirmed: 0.87, system_inferred: 0.65
- Retrieval user_explicit: 0.70, system_inferred: 0.45, external: 0.40
- Pending: 0.0 always (filtered before ranking, never surface as truth)

**Field-sensitive freshness** (FRESHNESS_PROFILES):
- pricing (offer_stack): 7-day half-life
- commitments: 5-day half-life
- project context: 14-day
- goals: 21-day
- business facts: 180-day
- tone/preferences: no decay (None)
- identity: no decay (None)
- wiki: 90-day, retrieval: 30-day

**Source bonus** (SOURCE_BONUS): Core State gets 1.2× for canonical queries, wiki gets 1.1× for pattern queries, audit gets 1.15× for history queries — prevents semantic relevance from overriding trust priority.

**Query-type routing** (detect_query_type):
- `canonical` → Core State first (pricing, goals, name, audience questions)
- `pattern` → wiki first (why, what patterns, what works)
- `history` → audit first (what changed, when did, history of)
- `general` → normal tiered order

**Confidence labels** grounded in trust_weight + freshness_mod (not raw score):
- High: trust ≥ 0.90, freshness ≥ 0.70
- Moderate: trust ≥ 0.65, freshness ≥ 0.40
- Low: trust ≥ 0.40
- Uncertain: trust < 0.40

**Golden test set:** 20 tests in ranking.py (all pass). Covers: layer ordering, trust floors, freshness math, pending filtered, confidence labels, query type detection, layer preference order.

**CLI:** `python3 ranking.py --test` / `--demo`

### Phase 5 — Response Behavior + Memory Usage Policy ✅ DONE 2026-04-12

**Artifacts:**
- `.claude/rules/memory-usage-policy.md` — behavioral policy read by IRIS every session
- `.claude/skills/memory/scripts/response_policy.py` — programmatic decision logic + golden tests

**The four modes:**
- `silent` — use memory, do not mention it (task execution, canonical queries with fresh Core State)
- `cite` — surface explicitly (wiki synthesis, stale already shown, strategy questions, history queries)
- `confirm` — ask before acting (contradiction detected, pending write triggered, stale + decision)
- `ignore` — do not use stored context (emotional state, no match, inferred source, low confidence)

**Key rules:**
- Emotional state always → ignore (never pull accountability context during venting)
- Pending write triggered → confirm (ingest detected an update)
- Contradiction with Core State → confirm
- Stale field + decision at stake → confirm once per session; cite if already confirmed
- Inferred/external source → ignore (never cite as user fact)
- Pending layer → ignore (0.0 trust, filtered before ranking)

**Pattern surfacing threshold:** 3+ instances, not emotional, not task execution, not shown in last 7 days, strategy/reflection context only. One observation max per session.

**Citation style** by memory type: Core State fresh → state cleanly (no citation), stale → "last confirmed [date] — still current?", wiki → "from what you've shared...", retrieval → "this came up before — still applies?". Never say "my records show" or "I remember you said."

**Anti-patterns list:** memory creep (referencing context every message), asking for confirmation when confidence is high, surfacing accountability during venting, overriding clear requests with stored preferences.

**Golden test set:** 20 conversation scenarios, 20/20 pass. Covers all 4 modes, edge cases (stale shown twice, inferred blocked, pending filtered, emotional override).

**CLI:** `python3 response_policy.py --test` / `--scenario`

### Phase 6 — Contradiction Flagging
- [ ] Add contradiction check to wiki write pipeline
- [ ] Set wiki page `status: contradiction_flagged` when detected
- [ ] Surface flagged pages in review queue
- [ ] Block retrieval citation of flagged pages until resolved

### Phase 6 — Pruning Loop
- [ ] Build stale detection (90-day wiki, 180-day index)
- [ ] Build duplicate similarity check
- [ ] Build promotion candidate detection
- [ ] Wire to `/memory lint` command
- [ ] Add human approval gate before any Core State promotion or bulk archive

### Phase 7 — MCPVault Integration (Obsidian bridge)
- [ ] Install and configure MCPVault
- [ ] Verify Claude can read/write `memory/wiki/` via MCP
- [ ] Confirm frontmatter schema is MCPVault-compatible
- [ ] Test end-to-end: ingest → wiki write → MCPVault read

---

## Appendix: What Already Exists in IRIS

The following infrastructure is already built and can be upgraded rather than rebuilt:

| Component | Location | Notes |
|---|---|---|
| `smart_search.py` | `.claude/skills/memory/scripts/` | Has BM25 + vector + temporal decay. Needs trust_weight layer added. |
| `auto_capture.py` | `.claude/skills/memory/scripts/` | Stop hook for fact extraction. Inactive — needs OPENAI_API_KEY. |
| `mem0_config.yaml` | `.claude/skills/memory/references/` | Points to Upstash. Update to Pinecone. |
| `memory_capture.py` | `.claude/hooks/` | Active Tier 1-2 hook. Keep as fallback. |
| `MEMORY.md` | `memory/` | Will become a human-readable view of Core State (auto-generated). |
| Daily logs | `memory/logs/` | Tier 2 session logs. Keep as-is. |
| `mem0_history.db` | `data/` | SQLite audit trail. Supplement with `audit-log.jsonl`. |

**Upstash references to remove:**
- `mem0_config.yaml` — change vector store to Pinecone
- `.env.example` — remove `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN`
- Any script importing Upstash client directly
