# Memory Protocol

Rules for how memory is managed across sessions.

## Source of Truth Hierarchy

**This order is absolute. Higher layers override lower layers.**

1. **`memory/core-state.json`** — Machine-readable canonical facts. Identity, goals, pricing, tone, commitments, active project. Written only by `core_state.py` with enforced write rules. Never edited directly.
2. **`memory/MEMORY.md`** — Human-readable summary. A projection of Core State, not a second source of truth. Do not edit MEMORY.md directly — update core-state.json instead, then regenerate MEMORY.md.
3. **`memory/logs/YYYY-MM-DD.md`** — Session-specific events. What happened today. Not a source of facts.

**The rule that prevents drift:**
> If MEMORY.md and core-state.json say different things, core-state.json wins. Always.

## At Session Start
1. Load `memory/core-state.json` via `core_state.py --context` for canonical facts
2. Read `memory/MEMORY.md` for human-readable context summary
3. Read today's log: `memory/logs/YYYY-MM-DD.md` (create if missing)
4. Read yesterday's log for continuity (if exists)

## During Session

### For canonical facts (pricing, goals, preferences, commitments):
- **Read:** Use `core_state.py --lookup <field>` or `--matches <query>` — never search for these
- **Write:** Only when user explicitly states or confirms a value
  - Single field: `core_state.py --write <field> <value> --source user_explicit --trigger "..."`
  - Multiple fields: `core_state.py --update '{"field": "value"}' --source user_confirmed --trigger "..."`
- **Validate after writes:** `core_state.py --validate`

### For session events and decisions:
- Append to today's log: `memory/logs/YYYY-MM-DD.md`
- Do not put session events in core-state.json

### MEMORY.md regeneration:
- MEMORY.md is a human-readable view of Core State
- Regenerate it after meaningful Core State updates with `mem0_sync_md.py` (when Tier 3 active) or by reading `core_state.py --context` and writing a fresh summary
- **Never edit MEMORY.md as if it were the source of truth** — edits will be overwritten on next regeneration

## Creating Daily Logs
If today's log doesn't exist, create it with this format:

```
# Daily Log: YYYY-MM-DD

> Session log for [Day, Month DD, YYYY]

---

## Events & Notes

```

## What Goes Where

| Content | Location | Notes |
|---|---|---|
| Pricing, goals, offers, identity | `core-state.json` | Deterministic lookup only |
| Tone preferences, commitments | `core-state.json` | Never inferred — only user-confirmed |
| Active project context | `core-state.json` | Set deliberately, cleared deliberately |
| Session events, decisions made | `logs/YYYY-MM-DD.md` | Append-only |
| Context summaries for humans | `MEMORY.md` | Auto-generated — do not edit directly |
| Contradiction flags | `logs/` or wiki | Surface to user, never auto-resolve |

## Tier 3: Pinecone Vector Memory (When Installed)

If `.claude/skills/memory/` exists with scripts and `PINECONE_API_KEY` is set:
- **Auto-capture is active** — the Stop hook handles fact extraction. Do not duplicate manually.
- **Search before deciding** — Run `smart_search.py --tiered` for full retrieval (Core State first, then vector).
- **Use the memory skill** for manual operations (add, search, sync, list, delete).
- **Core State is not replaced by Pinecone** — Pinecone is the search layer over wiki and indexed content. Core State is always looked up directly.

## Write Rules (enforced by core_state.py)

**Allowed to write to Core State:**
- `user_explicit` — user directly states a fact ("my price is now $997")
- `user_confirmed` — user confirms a proposed update ("yes, update that")
- `system_canonical` — output of an approved system workflow (iris-setup wizard, goal-setting skill)

**Blocked from writing to Core State:**
- `system_inferred` — AI guessed something from context
- `similarity_match` — retrieval result that looked relevant
- `raw_import` — unclassified note or article
- `external` — third-party content

**When a contradiction is detected:**
- IRIS flags it with both versions
- User decides which is correct
- Winning version is written with audit entry
- Losing version is archived, not deleted
- IRIS never silently resolves contradictions in Core State
