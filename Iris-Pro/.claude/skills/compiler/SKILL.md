---
name: compiler
description: Promotes raw silent-capture observations into structured vault knowledge. Reads the Iris Journal (friction, goals, commitments, energy) + the user's vault identity files, asks an LLM to propose vault updates (new Concepts/ articles, appends to Efforts/, flagged aspiration-vs-behavior gaps), and stores them as pending proposals. The user reviews each proposal and explicitly approves before anything is written to the vault. Use when the user wants to run a compiler pass, review pending proposals, or apply approved ones.
model: sonnet
---

# Compiler Skill

The "compiler" in Karpathy's compiler-analogy framework. Raw observations are the source code; the vault is the executable; this skill is the compiler that promotes raw → compiled.

## Core Principle: Propose, Never Apply

**The compiler never writes to the vault directly.** It generates proposals, stores them as `pending`, and waits for the user to explicitly approve each one. On approval, the user runs `apply` to write the change. This is the trust contract — the user always sees what's being added before it lands.

## The Flow

```
journal DBs + vault identity
        ↓
    compile.py
        ↓
  LLM reasoning
        ↓
proposals (pending) → data/compiler_proposals.db
        ↓
  review.py list          ← user inspects
  review.py show <id>     ← user reads full content
  review.py approve <id>  ← user approves (still not written)
  review.py apply <id>    ← NOW it writes to the vault
```

## Proposal Types

- **`new_concept`** — Creates a new file in `Concepts/`. Use when the LLM notices a pattern worth promoting to compiled knowledge. Safe: never overwrites existing files.
- **`append_to_effort`** — Appends content under a reserved section in an existing `Efforts/` file. Uses `vault_lib.append_to_section()` so user-authored content is never touched.
- **`observation`** — A flagged gap between aspirational content (vault identity files) and behavioral data (journal entries). Surfaced for review only — "applying" an observation just marks it acknowledged, no file is written.

**What the compiler will NOT propose:**
- Edits to `me.md`, `my-everest.md`, `my-business.md`, `my-voice.md` — identity files are user-owned
- Edits to `maps/iris-rules.md` — user's rules for IRIS
- Overwrites of any existing file
- Any write to `Calendar/` (that's the daily-notes layer, not the compiled layer)

## Operations

### Run the compiler
```bash
python3 .claude/skills/compiler/scripts/compile.py
python3 .claude/skills/compiler/scripts/compile.py --days 30
python3 .claude/skills/compiler/scripts/compile.py --format json
```

Reads the last 14 days of journal entries by default, loads vault identity files, calls the LLM, stores proposals as `pending`.

### Preview the prompt (no LLM call)
```bash
python3 .claude/skills/compiler/scripts/compile.py --dry-run
```

Shows the full system + user prompt that would be sent to the LLM. Useful for debugging or understanding what the compiler is seeing.

### Test without calling a real LLM
```bash
python3 .claude/skills/compiler/scripts/compile.py --mock-llm
```

Injects a synthetic LLM response so you can verify the storage + review flow without burning tokens.

### Review pending proposals
```bash
python3 .claude/skills/compiler/scripts/review.py list
python3 .claude/skills/compiler/scripts/review.py list --status approved
python3 .claude/skills/compiler/scripts/review.py show 12
```

### Approve or reject
```bash
python3 .claude/skills/compiler/scripts/review.py approve 12
python3 .claude/skills/compiler/scripts/review.py reject 12
```

### Apply approved proposals to the vault
```bash
python3 .claude/skills/compiler/scripts/review.py apply 12
python3 .claude/skills/compiler/scripts/review.py apply --all-approved
```

## Storage

- **`data/compiler_proposals.db`** — SQLite, one row per proposal. Lifecycle: `pending → approved → applied` (or `rejected`). Never deleted automatically.

## How IRIS Should Use This

- **When the user asks "what have you been noticing?"** — Run `review.py list --status applied` to see accepted observations, or `compile.py` to generate new proposals from recent journal data.
- **When the user says "let's do a review"** — Run `compile.py` to generate proposals, then walk through them one at a time with the user and call `approve`/`reject` based on their feedback.
- **Never apply proposals without explicit user approval.** Even if the user says "just do it", confirm each proposal first — this is the trust contract.
- **Always cite sources.** When presenting a proposal, include the `reasoning` and `source_entries` so the user can see why IRIS thinks this matters.

## Relationship to Other Skills

- **Reads from `iris-journal`** (subprocess call to `journal.py read --format json`). Journal is the authoritative source for behavioral data.
- **Reads from `vault`** (imports `vault_lib`). Vault is the authoritative source for aspirational/identity data.
- **Writes via `vault`** (on `apply`, calls `write_file` or `append_to_section` from `vault_lib`). Never touches the vault directly.
- **Does NOT write to the journal.** The journal is raw; the compiler is downstream.

## Future (not in MVP)

- **Dashboard UI** for proposal review (better UX than CLI)
- **Scheduled runs** via scheduled-tasks (daily compiler pass, surfaces batch via Telegram)
- **Identity file edit proposals** (requires extra trust scaffolding — not in MVP)
- **Cross-vault comparison** (if multiple vaults are connected — out of scope)
