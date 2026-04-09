---
name: iris-journal
description: Read-only unified view of everything IRIS has silently captured across her skills (friction-log, goal-decay-tracker, and future silent-capture skills). Shows what she's noticed, how she's tagged it, what state she's in on it, and what she's planning to do next. Use when the user wants to see what IRIS has been quietly tracking, ask "what have you been noticing?", or verify that silent capture is working.
model: haiku
---

# IRIS Journal

A chronological, read-only view into IRIS's silent observation layer. Everything she captures quietly — friction entries, goal mentions, pattern-watching decisions — surfaces here for the user to see on demand.

## Why This Exists

Many of IRIS's accountability skills capture silently — she logs what she notices without telling the user, so the experience doesn't feel like surveillance. But silent capture without visibility creates a trust gap: the user can't verify IRIS is actually working.

The journal closes that gap. It's the user's window into IRIS's internal observations. They can peek whenever they want, see exactly what she's been tracking, and understand what she's planning to do next.

## Core Principles

1. **Read-only from the user's side.** The journal is a record of what actually happened. The user cannot edit it directly. Corrections go through the underlying skills.
2. **Unified, chronological.** All silent-capture sources merge into a single time-ordered feed. No separate tabs for "friction" and "goals" — just what happened when.
3. **Computed state at read time.** State descriptions ("watching 2/3 before surfacing", "quiet for 12 days") are calculated when the journal is read, so they always reflect *now*, not the moment of capture.
4. **Honest tone.** The journal describes what IRIS is doing in plain language, including the reasoning. No marketing gloss.
5. **No new storage.** The journal doesn't have its own database. It reads from `friction_log.db` and `goals.db` (and any future skill DBs) and synthesizes on demand.

## Operations

### Read recent journal entries

```bash
python3 .claude/skills/iris-journal/scripts/journal.py read --days 7
```

Returns a chronological feed of everything IRIS silently captured in the last N days. Each entry includes:

- **Timestamp** — when IRIS captured it
- **Source** — which skill (friction-log, goal-decay-tracker)
- **Category/Type** — how IRIS tagged it
- **What** — the user's words verbatim
- **State** — computed at read time:
  - For friction: `watching (2/3 before surfacing)`, `surfaced`, `quiet` (no new occurrences in 14+ days)
  - For goals: `active (fresh)`, `active (approaching decay — X days until stale)`, `stale (X days quiet)`, `surfaced`, `archived`
- **Note** — IRIS's current "thought" on it, in plain language

### Read filtered by source

```bash
python3 .claude/skills/iris-journal/scripts/journal.py read --days 30 --source friction-log
python3 .claude/skills/iris-journal/scripts/journal.py read --days 30 --source goal-decay-tracker
```

### Summary view

```bash
python3 .claude/skills/iris-journal/scripts/journal.py summary
```

A high-level snapshot: how many items are being watched, how many patterns are forming, how many goals are active vs. stale vs. surfaced. No individual entries — just counts and current state.

### Output formats

Default output is JSON. For human-readable text:

```bash
python3 .claude/skills/iris-journal/scripts/journal.py read --days 7 --format text
```

## When To Use

- **User asks** "what have you been noticing?" / "what's in your journal?" / "show me what you've been tracking" → `read --days 7 --format text`
- **User wants verification** that silent capture is working → `summary`
- **User asks about a specific area** ("anything on friction lately?") → `read --source friction-log --format text`
- **User is debugging** or curious about why IRIS did or didn't surface something → `read` with relevant filter

## What Not To Do

- Do not proactively surface the journal. The user pulls it; IRIS does not push it.
- Do not edit any of the underlying skill databases from this skill. Journal is strictly read-only.
- Do not summarize or interpret the journal into a "receipts pull" of everything the user has done wrong. Present it neutrally.
- Do not expose the journal contents in other contexts (e.g., don't dump it into a Telegram message unprompted).

## How New Skills Plug In

Future silent-capture skills (Honest Re-Commit, Energy Mapping, etc.) should:

1. Write their data to their own SQLite DB under `data/`
2. Add a reader function to `journal.py` that queries their DB and returns normalized entries matching the journal format
3. Register the source name in the `SOURCES` dict at the top of `journal.py`

The journal will automatically include the new source in unified reads. No schema changes required.
