# AI OS — Architecture & Design Document

> Give this document + the aios/ folder to any AI or human. They'll understand the full system, why every decision was made, and how to extend it.

---

## What This Is

The AI OS is a Claude Code workspace structured as an operating system. It turns a folder on your machine into a persistent, intelligent business assistant that:

- Knows your business (context files filled by a setup wizard)
- Writes in your voice (voice guide captured during setup)
- Runs structured workflows (25 skills — from research to slide generation)
- Remembers across sessions (3-tier memory system)
- Enforces safety rules (hooks that block dangerous actions)
- Delegates to specialists (3 custom agents with restricted permissions)
- Grows with you (create new skills for any repeatable workflow)

It requires only a Claude Code subscription ($20-200/mo). No other API keys for the core 7 starter skills. Power skills unlock with optional API keys.

---

## Why It Exists

### The Problem

People sell Claude Code "templates" — a folder structure with a system prompt — for $997 via webinar funnels. The framing is actually correct: Claude Code is a "harness" (not a wrapper), and structuring it well is the key to getting value. But a folder structure is not worth $997.

Meanwhile, other implementations exist:
- **Obie Fernandez** built a CTO OS — real results (11K lines of institutional knowledge in 3 weeks), but it's all advisory. Claude reasons about everything. No deterministic scripts. This works for processing meeting notes but fails at multi-step pipelines where accuracy matters.
- **Bijit Ghosh** wrote the conceptual framework (Skills = OS applications, Model = processor) but never built anything.

### The Gap We Fill

**Separation of concerns.** AI reasoning handles the WHAT (decisions, analysis, creative judgment). Deterministic scripts handle the HOW (API calls, data processing, file operations). This is what makes the difference:

```
All-advisory (Obie's approach):
  90% accuracy × 90% × 90% × 90% × 90% = 59% over 5 steps

Separation of concerns (AI OS approach):
  AI decides WHAT (90%) → Scripts execute HOW (99.9%) = consistent results
```

Our lead research pipeline: 7 scripts, $0.40/lead, 45-60 seconds, consistent results. That's not possible when Claude does everything itself.

### Why Not Just a Plugin?

The AI OS is MORE than a plugin. It's a workspace template — a complete environment with writable directories (context/, memory/, data/) that get personalized to the user's business. Plugins are read-only packages that install components INTO an existing workspace. The AI OS IS the workspace.

Individual skill packs (like a content-pack or sales-pack) can be plugins. The full OS template is distributed as a GitHub repo or folder.

---

## The OS Analogy

Every piece of the AI OS maps to a real operating system concept:

```
+--------------------------------------------------------------+
|                      AI OPERATING SYSTEM                      |
|                                                               |
|  PROGRAMS         WORKERS          PACKAGE MANAGER            |
|  .claude/skills/  .claude/agents/  plugin.json                |
|  25 skills        3 agents         Distributable bundles      |
|                                                               |
|  SECURITY LAYER — Hooks                                       |
|  Stop → memory    PreToolUse → guardrails                     |
|  PostToolUse → validation                                     |
|                                                               |
|  MEMORY — 3 Tiers                                             |
|  MEMORY.md (always loaded) → daily logs → vectors (optional)  |
|                                                               |
|  KERNEL           CONFIG           FILESYSTEM                 |
|  CLAUDE.md        args/*.yaml      context/                   |
|  .claude/rules/   preferences      voice, business, ICP       |
+--------------------------------------------------------------+
```

| OS Concept | AI OS Equivalent | What It Does |
|------------|-----------------|-------------|
| **Kernel** | CLAUDE.md + .claude/rules/ | System instructions. How the AI thinks and operates. |
| **Programs** | .claude/skills/ | Self-contained workflows. Auto-discovered by description matching. |
| **Security** | hooks/ | Lifecycle hooks that fire on events. Block dangerous commands, capture memory, validate output. |
| **Workers** | .claude/agents/ | Specialized subprocesses with restricted tools and cheaper models. |
| **Filesystem** | context/ | Domain knowledge — business details, voice guide, ICP. |
| **Config** | args/*.yaml | Runtime behavior settings. Change behavior without editing skills. |
| **Memory** | memory/ | Persistent storage across sessions. 3 tiers: core → session → vectors. |
| **Databases** | data/*.db | SQLite for structured data (tasks, tracking, analytics). |
| **Cron** | `claude -p` headless | Schedule skills to run automatically via crontab. |
| **Drivers** | MCP servers | External service access (Notion, Slack, YouTube, etc.). Optional. |
| **Package Mgr** | plugin.json | Bundle and distribute skills + hooks + agents. |

---

## File Structure (Complete)

```
aios/
├── CLAUDE.md                                    # KERNEL — System instructions (~80 lines)
├── ARCHITECTURE.md                              # THIS FILE — Full system documentation
├── README.md                                    # Public-facing README with quickstart
├── LICENSE                                      # MIT
├── install.sh                                   # One-command setup script
├── setup_memory.py                              # Memory system installer (mem0 + Upstash Vector)
├── plugin.json                                  # Plugin manifest for distribution
├── .env.example                                 # API key template
├── .gitignore                                   # Secrets, logs, databases excluded
│
├── .claude/
│   ├── settings.json                            # Default permissions
│   ├── settings.local.json.example              # Template: hooks + permissions
│   │
│   ├── rules/                                   # MODULAR RULES (part of kernel)
│   │   ├── guardrails.md                        # Safety rules
│   │   └── memory-protocol.md                   # Memory management rules
│   │
│   ├── skills/                                  # PROGRAMS — 25 skills
│   │   │
│   │   │  # === STARTER SKILLS (zero config) ===
│   │   ├── iris-setup/                          # Setup wizard (THE killer feature)
│   │   │   ├── SKILL.md                         # 5-phase questionnaire → auto-configure
│   │   │   └── scripts/
│   │   │       └── init_business.py             # Writes context files from answers
│   │   │
│   │   ├── research/                            # Deep research (WebSearch, no API keys)
│   │   │   └── SKILL.md
│   │   │
│   │   ├── content-writer/                      # Write in user's voice
│   │   │   └── SKILL.md                         # Delegates to content-writer agent
│   │   │
│   │   ├── meeting-prep/                        # Research + talking points
│   │   │   └── SKILL.md                         # Uses research skill internally
│   │   │
│   │   ├── email-assistant/                     # Paste-based email triage + drafts
│   │   │   └── SKILL.md                         # No API keys needed
│   │   │
│   │   ├── weekly-review/                       # Structured weekly review
│   │   │   ├── SKILL.md                         # Reads 7 days of logs
│   │   │   └── scripts/
│   │   │       └── weekly_metrics.py            # Parses logs for patterns
│   │   │
│   │   ├── task-manager/                        # SQLite task tracking
│   │   │   ├── SKILL.md                         # add/list/complete/update/delete
│   │   │   └── scripts/
│   │   │       └── task_db.py                   # All CRUD operations
│   │   │
│   │   ├── skill-creator/                       # Meta-skill: create new skills
│   │   │   ├── SKILL.md                         # 8-step creation process
│   │   │   ├── scripts/
│   │   │   │   └── init_skill.py                # Scaffolds skill directories
│   │   │   └── references/
│   │   │       ├── frontmatter-guide.md         # How to write good frontmatter
│   │   │       └── patterns.md                  # Skill design patterns
│   │   │
│   │   │  # === POWER SKILLS (optional API keys) ===
│   │   ├── research-lead/                       # LinkedIn → research + outreach
│   │   │   ├── SKILL.md                         # 6-step pipeline, parallel analysis
│   │   │   └── scripts/                         # 9 scripts (scrape, research, analyze...)
│   │   │
│   │   ├── content-pipeline/                    # YouTube → LinkedIn posts + carousels
│   │   │   └── SKILL.md                         # 7-step content transformation
│   │   │
│   │   ├── email-digest/                        # Gmail → sentiment → Slack briefing
│   │   │   └── SKILL.md                         # Automated inbox processing
│   │   │
│   │   ├── gamma-slides/                        # Markdown → Gamma presentations
│   │   │   ├── SKILL.md
│   │   │   └── scripts/
│   │   │       └── create_presentation.py       # Gamma API wrapper with polling
│   │   │
│   │   ├── build-website/                       # PRISM framework → static sites
│   │   │   └── SKILL.md                         # 6-phase design + build process
│   │   │
│   │   ├── build-app/                           # ATLAS framework → full-stack apps
│   │   │   └── SKILL.md                         # 5-phase architect → stress-test
│   │   │
│   │   ├── memory/                              # mem0 + Upstash Vector persistent memory
│   │   │   ├── SKILL.md                         # Search, add, sync, list, delete
│   │   │   ├── scripts/
│   │   │   │   ├── mem0_client.py               # Factory + secret sanitizer
│   │   │   │   ├── auto_capture.py              # Stop hook (automatic extraction)
│   │   │   │   ├── smart_search.py              # Hybrid BM25+vector+temporal+MMR
│   │   │   │   ├── mem0_search.py               # Basic vector search
│   │   │   │   ├── mem0_add.py                  # Manual memory add + FTS5 indexing
│   │   │   │   ├── mem0_list.py                 # List all (fallback to history DB)
│   │   │   │   ├── mem0_delete.py               # Single or bulk delete
│   │   │   │   ├── mem0_sync_md.py              # Sync mem0 → MEMORY.md
│   │   │   │   └── daily_log.py                 # Session log writer
│   │   │   └── references/
│   │   │       └── mem0_config.yaml             # mem0 + Upstash Vector configuration
│   │   │
│   │   └── telegram/                            # Telegram mobile access
│   │       ├── SKILL.md                         # Bot daemon with mem0 integration
│   │       ├── scripts/
│   │       │   ├── telegram_handler.py          # Core daemon (poll → Claude → respond)
│   │       │   ├── telegram_bot.py              # Polling + security validation
│   │       │   ├── telegram_send.py             # Telegram Bot API wrapper
│   │       │   └── message_db.py                # SQLite message history
│   │       └── references/
│   │           └── messaging.yaml               # Bot config (whitelist, rate limits)
│   │
│   └── agents/                                  # WORKERS — 3 subagents
│       ├── researcher.md                        # Sonnet, read-only tools
│       ├── content-writer.md                    # Sonnet, Read + Write + Glob only
│       └── code-reviewer.md                     # Opus, read-only tools
│
├── context/                                     # FILESYSTEM — Domain knowledge
│   ├── my-business.md                           # Placeholder → filled by setup wizard
│   ├── my-voice.md                              # Placeholder → filled by setup wizard
│   └── README.md
│
├── args/                                        # CONFIG — Runtime settings
│   ├── preferences.yaml                         # Timezone, model routing, defaults
│   └── README.md
│
├── memory/                                      # MEMORY — 3-tier persistence
│   ├── MEMORY.md                                # Tier 1: always loaded (~200 lines)
│   ├── logs/                                    # Tier 2: daily session logs
│   │   └── .gitkeep
│   └── README.md
│
├── data/                                        # DATABASES — SQLite storage
│   └── .gitkeep                                 # tasks.db created at runtime
│
├── hooks/                                       # SECURITY — Lifecycle hooks
│   ├── memory_capture.py                        # Stop hook: daily log management
│   ├── guardrail_check.py                       # PreToolUse: block dangerous commands
│   └── validate_output.py                       # PostToolUse: validate JSON output
│
├── .tmp/                                        # SCRATCH — Disposable temp files
│   └── .gitkeep
│
└── docs/                                        # DOCUMENTATION
    ├── SKILLS-GUIDE.md                          # How to create custom skills
    ├── MCP-SERVERS.md                           # Add external service access
    ├── AUTOMATION.md                            # Cron + headless mode scheduling
    ├── MEMORY-UPGRADE.md                        # mem0 + Upstash Vector (Tier 3 memory)
    └── UPGRADE-PATHS.md                         # Gmail, Telegram, n8n, vectors
```

**Stats:** 72 files, 40 directories.

---

## Key Design Decisions

### 1. Skills Replace Goals + Tools

In the predecessor system (GOTCHA framework), goals/ defined what to do and tools/ contained the scripts. In v2, skills unify both into self-contained packages:

```
.claude/skills/email-digest/
├── SKILL.md          # What to do (was the goal)
├── scripts/          # How to do it (were in tools/)
├── references/       # Supporting docs
└── assets/           # Templates, fonts
```

**Why:** Self-containment. Each skill is portable, discoverable (Claude matches descriptions automatically), and can specify its own model, isolation, and tool restrictions via frontmatter.

### 2. CLAUDE.md Is Lean (~80 lines)

The kernel is instructions only. No philosophy, no framework explanation, no "why this structure exists" sections. Claude needs to know WHAT to do, not WHY the architecture exists.

Detailed rules go in `.claude/rules/*.md` (modular, loaded automatically). Detailed skill instructions go in each skill's SKILL.md (loaded on demand, not every session).

### 3. Zero API Keys for Core

The 7 starter skills work with ONLY a Claude Code subscription. No OpenAI key, no Upstash, no Gmail API. This means:

- `research` uses WebSearch (built into Claude Code)
- `email-assistant` works by paste (user pastes email text)
- `task-manager` uses SQLite (standard library)
- `content-writer` uses Claude's reasoning (no external calls)
- `memory` uses MEMORY.md + daily logs (plain files)

Power skills unlock with optional API keys. This keeps the onboarding friction at zero.

### 4. Memory Is 3-Tier

```
Tier 1: MEMORY.md        → Always in prompt. Curated facts. ~200 lines.
Tier 2: Daily logs        → Session history. Append-only. Read at session start.
Tier 3: mem0 + Upstash    → Optional. Cloud vectors. Semantic search. Auto-dedup.
```

Tier 1+2 ship as default (zero config). Tier 3 is documented as an upgrade in docs/MEMORY-UPGRADE.md. The mem0 system costs ~$0.04/month with Upstash Vector's free tier (10K queries/day, 200M vector dimensions). It automatically extracts facts, deduplicates them (ADD/UPDATE/DELETE/NOOP), and resolves contradictions.

### 5. Hooks for Safety, Not Just Automation

Three hook types:
- **Stop** (after every response) — Memory capture. Runs async, invisible.
- **PreToolUse** (before dangerous commands) — Guardrails. Blocks rm -rf, force-push, credential exposure. Exit code 2 = blocked.
- **PostToolUse** (after script execution) — Validates JSON output from scripts.

Hooks are deterministic safety nets. Claude can be convinced to ignore a rule in CLAUDE.md. It cannot bypass a hook that returns exit code 2.

### 6. Agents Are Specialists With Restrictions

Three agents, each with a specific model and tool set:

| Agent | Model | Tools | Why This Config |
|-------|-------|-------|----------------|
| researcher | Sonnet | Read, Glob, Grep, WebSearch | Cheaper model for research. Can't modify files. |
| content-writer | Sonnet | Read, Write, Glob | Writes content but can't execute code or access APIs. |
| code-reviewer | Opus | Read, Grep, Glob | Best reasoning for review. Can't modify anything. |

Skills delegate to agents via `agent:` frontmatter. The parent (Opus) reads the skill, decides which agent to use, and spawns a subagent with restricted permissions.

### 7. Model Routing for Cost

Skills specify which model runs them:

```yaml
model: haiku    # Simple tasks: formatting, classification (~$0.25/M tokens)
model: sonnet   # Most pipelines: research, content, email (~$3/M tokens)
model: opus     # Complex reasoning: architecture, creative work (~$15/M tokens)
```

Combined with `context: fork`, this spawns a cheaper subagent. A content pipeline running on Sonnet costs ~5x less than running on Opus, with comparable quality for structured tasks.

### 7b. Provider-Agnostic AI Backend

Python scripts route reasoning calls through `lib/ai_provider.py`, which supports multiple LLM providers. Users aren't locked into any single provider.

**How it works:**

| Layer | What It Controls | Provider |
|-------|-----------------|----------|
| **Orchestration** (Claude Code harness) | Skill routing, subagents, frontmatter `model:` | Always Anthropic |
| **Script reasoning** (`ai.reason()` calls) | Python script AI calls | User's choice |

**Switching providers:**
1. Set `AI_PROVIDER=openai` (or `google`, `anthropic`) in `.env`
2. Set the corresponding API key
3. `pip install litellm` (not needed for `claude-cli`)

**Abstract tiers** decouple scripts from specific models:

```python
ai.reason(system, msg, tier="default")    # Everyday work
ai.reason(system, msg, tier="fast")       # Low latency
ai.reason(system, msg, tier="cheap")      # High volume
ai.reason(system, msg, tier="powerful")   # Complex reasoning
```

Tiers map to provider-specific models in `args/preferences.yaml`. Update the mapping when new models release — no code changes needed. Legacy names (`opus`, `sonnet`, `haiku`) still work and auto-map to tiers.

### 8. Python Scripts Over MCP for Frequent Operations

MCP servers add ~15K tokens each to context. 4 servers = 60K tokens overhead. Python scripts calling APIs directly via `requests` are cheaper for operations that happen frequently or follow the same pattern every time.

**Use MCP when:** Claude needs to reason about WHAT to query (exploration).
**Use scripts when:** The query is always the same (pipeline step).

### 9. Distribution = GitHub Repo, Not Plugin

The AI OS is a workspace template (writable context/, memory/, data/). Plugins are read-only packages. So:

- **Full OS** → GitHub repo (git clone for devs, Download ZIP for non-coders)
- **Skill packs** → Could be plugins (content-pack, sales-pack, ops-pack)
- **install.sh** → Handles initialization after download

---

## How It Works (End to End)

### First Run

1. User downloads the folder (git clone or ZIP)
2. Runs `./install.sh` → creates directories, copies templates
3. Runs `claude` → CLAUDE.md loads as system prompt
4. CLAUDE.md detects `context/my-business.md` is a placeholder
5. Triggers `iris-setup` skill automatically
6. Setup wizard asks 15 questions across 4 phases
7. Writes `context/my-business.md` and `context/my-voice.md`
8. Updates `args/preferences.yaml` and `memory/MEMORY.md`
9. System is configured for THIS business

### Normal Session

1. Claude starts, loads CLAUDE.md + .claude/rules/ + MEMORY.md
2. Reads today's daily log and yesterday's for continuity
3. User asks for something: "Write a LinkedIn post about AI automation"
4. Claude matches the request to the `content-writer` skill
5. Skill loads: reads voice guide, business context, writes in the user's voice
6. User gets content that sounds like them, not like AI
7. Stop hook fires (async) → daily log updated
8. Session continues

### Automation

1. Cron job fires: `claude -p "/weekly-review" --output-format json`
2. Claude loads headlessly, triggers weekly-review skill
3. Reads 7 days of daily logs, MEMORY.md goals
4. Produces structured review + next week's plan
5. Output logged to `data/cron.log`

---

## How to Test in a New Environment

1. Copy the entire `aios/` folder to a new location
2. `cd aios && chmod +x install.sh && ./install.sh`
3. `claude`
4. Say: "Set up my business" → walk through the wizard
5. Test each skill:
   - "Research [topic]"
   - "Write a LinkedIn post about [topic]"
   - "Prep for meeting with [person]"
   - "Add a task: follow up with someone"
   - "What's on my plate?"
   - "Weekly review"
   - "Create a skill for [workflow]"

### What to Update/Fix

When testing, focus on:
- **Description matching** — Does Claude find the right skill? If not, tweak the description in the SKILL.md frontmatter.
- **Voice quality** — Does content sound like the user after setup? If not, refine context/my-voice.md.
- **Script errors** — Do Python scripts run? Check Python path (python3 vs python3.11).
- **Memory persistence** — Does MEMORY.md update? Do daily logs get created?
- **Hook behavior** — Does the guardrail hook block `rm -rf`? Test it.

---

## How to Extend

### Add a New Skill

```
"Create a skill for [describe your workflow]"
```

Or manually: `python3 .claude/skills/skill-creator/scripts/init_skill.py my-skill`

### Add Context Files

Drop new markdown files in `context/`:
- `context/my-icp.md` — Ideal customer profile
- `context/case-studies.md` — Client success stories
- `context/competitors.md` — Competitive landscape

Skills reference these automatically when relevant.

### Add MCP Servers

Edit `.claude/settings.local.json` — see docs/MCP-SERVERS.md for configs.

### Upgrade Memory

Follow docs/MEMORY-UPGRADE.md to add mem0 + Upstash Vector (Tier 3).

### Add Hooks

Edit `.claude/settings.local.json` to add hooks for new lifecycle events. See the settings.local.json.example for the format.

---

## What This System Beats

| System | Has | Doesn't Have |
|--------|-----|-------------|
| **Obie's CTO OS** | Real skills, MCP, results | Scripts, hooks, agents, separation of concerns |
| **$997 templates** | Marketing, community | Specifics, battle-testing, open source |
| **Bijit's conceptual OS** | Good framing | Any implementation |
| **Claude's auto-memory** | Simple persistence | Dedup, semantic search, tiered architecture |
| **Raw Claude Code** | Everything above as primitives | Structure, workflows, business context |

**This system** = structured workspace + separation of concerns + 25 skills + 3 agents + 3-tier memory + hooks + setup wizard + zero-config starter + documented upgrade paths. Built over 6+ months of production use.

---

## Cost Summary

| Component | Cost |
|-----------|------|
| Claude Code subscription | $20-200/month |
| Core skills (7 starter) | $0 additional |
| Power skills (API keys) | Varies by usage |
| mem0 memory (optional) | ~$0.04/month |
| Upstash Vector storage | Free (10K queries/day) |
| Lead research pipeline | ~$0.40/lead |
| **Minimum viable AI OS** | **$20/month** (Claude Pro) |
