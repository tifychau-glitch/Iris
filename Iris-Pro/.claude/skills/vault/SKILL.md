---
name: vault
description: Read, write, and scaffold the user's Obsidian vault (their second brain). Use when IRIS needs to read identity files (me.md, my-everest.md, my-voice.md, my-business.md), append check-ins to daily notes, create new concept articles, or initialize a starter vault for a new user. Vault location is set via IRIS_VAULT_PATH in .env.
model: haiku
---

# Vault Skill

Manages read and write access to the user's Obsidian vault. The vault lives outside the Iris project (default: `~/Documents/Iris Vault`) and is plain markdown on the local filesystem — no git, no sync layer, no cloud.

## Philosophy

- **User owns the vault.** IRIS reads from it and writes only to reserved sections. User-authored content is never modified.
- **Append-only to reserved sections.** When IRIS writes to a file the user also edits (like `Calendar/YYYY-MM-DD.md`), she appends under a reserved `## Iris Check-ins` heading. Never edits existing content.
- **Refuse to overwrite files by default.** `write_file` returns an error unless `overwrite=True` is passed explicitly.
- **Path traversal blocked.** Relative paths with `..` or absolute paths are rejected.

## Operations

### Load vault context at session start (Phase 2 — most common use)
```bash
python3 .claude/skills/vault/scripts/vault_context.py
python3 .claude/skills/vault/scripts/vault_context.py --format json
python3 .claude/skills/vault/scripts/vault_context.py --quiet  # silent if no vault
```

Returns a single formatted markdown document with:
- `index.md` — vault navigation map
- `me.md`, `my-everest.md`, `my-business.md`, `my-voice.md` — identity files
- `maps/iris-rules.md` — user's rules for IRIS
- The most recent `Calendar/YYYY-MM-DD.md` — for continuity

Handles missing vault gracefully — returns an "unavailable" status instead of erroring. IRIS runs this at the start of every returning-user conversation (see IRIS.md → Vault Context section).

### Read a file
```bash
python3 .claude/skills/vault/scripts/vault_read.py --file me.md
python3 .claude/skills/vault/scripts/vault_read.py --file Calendar/2026-04-09.md --format json
```

### List files
```bash
python3 .claude/skills/vault/scripts/vault_read.py --list
python3 .claude/skills/vault/scripts/vault_read.py --list --subfolder Efforts
python3 .claude/skills/vault/scripts/vault_read.py --list --pattern "*.md" --format json
```

### Append under a reserved section
```bash
python3 .claude/skills/vault/scripts/vault_write.py --append \
    --file Calendar/2026-04-09.md \
    --section "Iris Check-ins" \
    --content "09:30 — What's the one thing today?"
```

Creates the file if it doesn't exist. Creates the `## Iris Check-ins` heading if missing. Appends below existing entries in the same section. Never touches other sections.

### Create a new file
```bash
python3 .claude/skills/vault/scripts/vault_write.py --create \
    --file Concepts/shipping-patterns.md \
    --content "# Shipping Patterns\n\nObservations..."
```

Refuses to overwrite existing files. Add `--overwrite` only for intentional replacement (e.g., regenerating synthesized concept articles with user approval).

### Scaffold a new vault (called by the dashboard "Connect Vault" flow)
```bash
python3 .claude/skills/vault/scripts/vault_init.py ~/Documents/Iris\ Vault
python3 .claude/skills/vault/scripts/vault_init.py /custom/path --force
```

Creates folders (`maps/`, `Calendar/`, `Efforts/`, `Atlas/`, `Concepts/`) and writes starter files from `templates/`. Refuses to scaffold into a folder that already contains `.md` files unless `--force` is passed (force still won't overwrite existing files).

## Starter Vault Structure

When `vault_init.py` runs, it creates:

```
Iris Vault/
├── README.md              ← explains the folder structure to the user
├── index.md               ← navigation file (IRIS reads this first in Phase 2)
├── me.md                  ← identity: who the user is, values, first principles
├── my-everest.md          ← 3-5 year vision
├── my-voice.md            ← how the user writes and communicates
├── my-business.md         ← what they're building
├── maps/
│   ├── vault-map.md       ← deeper structure guide
│   └── iris-rules.md      ← user's instructions to IRIS
├── Calendar/              ← daily notes (YYYY-MM-DD.md)
├── Efforts/               ← active projects
├── Atlas/                 ← reference material, clippings, saved articles
└── Concepts/              ← synthesized insights (compiler promotes here in Phase 3)
```

All starter files are pre-filled with guidance prompts in HTML comments that the user can replace with their own content.

## Config

- **`IRIS_VAULT_PATH`** — absolute path to the vault folder. Set via the dashboard "Connect Vault" card or manually in `.env`. Expands `~`.
- **Default location:** `~/Documents/Iris Vault` (cross-platform via `Path.home()`).

## Imports (for use in other skills)

Other skills that need to read/write the vault import from `vault_lib.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "vault" / "scripts"))

from vault_lib import (
    get_vault_path,
    read_file,
    write_file,
    append_to_section,
    list_files,
)
```

## What this skill does NOT do (yet)

- **Does not read `index.md` as a navigation layer.** That's Phase 2 — IRIS will update her conversation startup to read `index.md` + identity files before responding.
- **Does not generate synthesized insights.** That's Phase 3 — the `compiler` skill reads the Iris Journal + vault, proposes concept articles, user approves.
- **Does not lint `me.md` for model portability.** Phase 4.
- **Does not search the vault semantically.** At current vault sizes, grep or direct reads are faster. Semantic search is a Phase 5 fallback.

## Security

- Path traversal (`..`) blocked at the library level.
- Absolute paths rejected (all operations are anchored to `IRIS_VAULT_PATH`).
- Symlink escapes caught via `Path.resolve() + relative_to()` containment check.
- Refuses to scaffold into a folder that already contains markdown files (prevents accidental clobbering of an existing vault).
- `vault_init.py` never overwrites existing files during scaffolding — if a starter file already exists, it's skipped.
