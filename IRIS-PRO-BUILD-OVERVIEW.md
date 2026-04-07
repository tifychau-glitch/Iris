# Iris Pro Build — Full Project Overview

> Last updated: April 4, 2026
> Purpose: Give an external AI (or collaborator) a clear picture of where the Iris Pro build currently stands.

---

## What Is Iris?

Iris is an **AI-powered business operating system** that transforms Claude Code into a full business workspace. It maps traditional OS concepts to AI-driven automation:

| OS Concept | Iris Equivalent | Location |
|---|---|---|
| Kernel | `CLAUDE.md` (system instructions) | Root |
| Programs | 18 Skills (self-contained workflows) | `.claude/skills/` |
| Workers | 3 Specialized agents (restricted subagents) | `.claude/agents/` |
| Security | Hooks (lifecycle event handlers) | Root + `.claude/rules/` |
| Filesystem | Context knowledge files | `context/` |
| Config | Runtime preferences | `args/` |
| Memory | 3-tier system (core, session, vectors) | `memory/` |
| Database | SQLite for structured data | `data/` |
| Cron | Headless mode (`claude -p`) | Scripts |

Built by **Tiffany Chau**. Tagline: *"Turn Claude Code into your AI business operating system."*

---

## The Three Products

| | Iris Core | Iris Pro | AI OS Template |
|---|---|---|---|
| **Type** | Free Telegram accountability bot | Full commercial workspace | Open-source base template |
| **Interface** | Telegram only | Claude Code IDE | Claude Code IDE |
| **Skills** | N/A | 18 skills + 3 agents | 18 skills + 3 agents |
| **Memory** | Basic SQLite | 3-tier (core + logs + vectors) | 3-tier |
| **License** | Proprietary | Proprietary | MIT |
| **Location** | `/Iris-Core/` | `/Iris-Pro/` | `/Iris-AI-OS-Template/` |

There's also an **`iris-landing-page/`** directory with the marketing site (HTML, 4-tier pricing).

---

## Iris Pro — Current Architecture

### Directory Structure

```
Iris-Pro/
├── CLAUDE.md                   # ~500 lines — system handbook, personality, behavior rules
├── ARCHITECTURE.md             # ~460 lines — design decisions & extension patterns
├── README.md                   # Public marketing/overview
├── setup.sh                    # One-command initialization
├── .env.example                # API key template
├── plugin.json                 # Manifest (all skills, agents, hooks)
│
├── .claude/
│   ├── settings.json           # Default permissions
│   ├── skills/                 # 18 skills (each with SKILL.md + scripts/)
│   ├── agents/                 # 3 agents (researcher, content-writer, code-reviewer)
│   └── rules/                  # Modular rule files
│       ├── guardrails.md       # Safety rules
│       ├── memory-protocol.md  # Memory management
│       └── dashboard-updates.md
│
├── context/
│   ├── my-business.md          # Business profile (filled by setup wizard)
│   ├── my-voice.md             # Voice/tone guide
│   └── README.md
│
├── memory/
│   ├── MEMORY.md               # Persistent brain (always loaded, ~200 lines)
│   ├── logs/                   # Daily session logs (YYYY-MM-DD.md)
│   └── README.md
│
├── data/                       # SQLite databases (tasks.db, messages.db, etc.)
├── args/
│   └── preferences.yaml        # Runtime config (timezone, model routing, defaults)
├── hooks/
│   ├── memory_capture.py       # Stop hook — auto-capture to daily log + memory
│   ├── guardrail_check.py      # PreToolUse — blocks destructive commands
│   └── validate_output.py      # PostToolUse — validates JSON script output
│
└── docs/
    ├── SKILLS-GUIDE.md         # How to create custom skills
    ├── MCP-SERVERS.md          # External service access
    ├── AUTOMATION.md           # Cron + headless mode
    ├── MEMORY-UPGRADE.md       # mem0 + Pinecone setup
    └── UPGRADE-PATHS.md        # 7 upgrade tiers
```

---

## All 18 Skills

### Starter Skills (Zero Config — just need Claude Code + Anthropic key)

| # | Skill | Trigger | What It Does |
|---|---|---|---|
| 1 | `iris-setup` | First run / "set up my business" | 5-phase business configuration wizard |
| 2 | `research` | "research X", "look into X" | Deep research on any topic (competitors, markets, tech) |
| 3 | `content-writer` | "write a post about X" | Creates content in user's voice (LinkedIn, email, blog, etc.) |
| 4 | `meeting-prep` | "prep for meeting with X" | Research briefs, talking points, follow-up templates |
| 5 | `email-assistant` | "help with this email" | Paste-based email triage, drafting, summarizing |
| 6 | `weekly-review` | "weekly review" | Structured weekly business review and planning |
| 7 | `task-manager` | "add a task", "what's on my plate" | SQLite-backed task/project tracking |
| 8 | `skill-creator` | "create a skill" | Meta-skill: packages workflows into new skills |

### Power Skills (Require additional API keys)

| # | Skill | Keys Needed | What It Does |
|---|---|---|---|
| 9 | `research-lead` | Relevance AI, Perplexity, OpenAI | LinkedIn URL to full research package + outreach DMs |
| 10 | `content-pipeline` | (none extra) | YouTube transcript to LinkedIn posts + carousel PDFs |
| 11 | `email-digest` | Gmail API, Slack Bot Token | Gmail inbox to sentiment analysis + Slack briefing |
| 12 | `gamma-slides` | Gamma API key | Markdown to presentation slide decks |
| 13 | `build-website` | (none extra) | PRISM framework: 6-phase static site builder (Astro + Tailwind + GSAP) |
| 14 | `build-app` | (none extra) | ATLAS framework: 5-phase full-stack app builder (Next.js/React + Supabase) |
| 15 | `memory` | OpenAI, Pinecone | mem0 + Pinecone vector memory (semantic search, dedup) |
| 16 | `telegram` | Telegram Bot Token + all core keys | Mobile bot access via polling daemon |
| 17 | `iris-accountability-engine` | (none extra) | Commitment tracking with 5 dynamic tone/personality levels |
| 18 | `plugin-builder` | (none extra) | Package skills into distributable Claude Code plugins |

### Additional Skills (referenced in session)

| Skill | What It Does |
|---|---|
| `controlled-calendar` | Intentional calendar design and maintenance |
| `mt-everest` | 3-5 year north-star goal framework with coaching |

---

## 3 Specialized Agents

| Agent | Model | Tools | Purpose |
|---|---|---|---|
| `researcher` | Sonnet | Read, Glob, Grep, WebSearch, WebFetch | Read-only deep research with synthesis |
| `content-writer` | Sonnet | Read, Write, Glob | Voice-preserving content creation |
| `code-reviewer` | Opus | Read, Grep, Glob | Code quality + security analysis (read-only) |

All agents run as isolated subagents (`context: fork`) with restricted tool sets and cheaper models where possible.

---

## 3-Tier Memory System

| Tier | What | Storage | Cost | Always Loaded? |
|---|---|---|---|---|
| **1. MEMORY.md** | Curated facts — goals, preferences, business context | `memory/MEMORY.md` | Free | Yes |
| **2. Daily Logs** | Session history, auto-captured per day | `memory/logs/YYYY-MM-DD.md` | Free | Referenced at session start |
| **3. Vector Memory** | Semantic search via mem0 + Pinecone | Pinecone cloud | ~$0.04/month | On-demand search |

- Tier 1+2 work out of the box with zero cost
- Tier 3 is an optional upgrade requiring OpenAI + Pinecone API keys
- The `Stop` hook auto-captures facts after every response
- Vector memory handles deduplication and contradiction resolution

---

## Hooks (Lifecycle Events)

| Hook | Timing | Purpose |
|---|---|---|
| `memory_capture.py` | **Stop** (after every response) | Auto-capture key facts to daily log + MEMORY.md |
| `guardrail_check.py` | **PreToolUse** (before dangerous commands) | Blocks `rm -rf`, force-push, credential exposure (exit code 2 = hard block) |
| `validate_output.py` | **PostToolUse** (after script execution) | Validates JSON output from skill scripts |

---

## Skill Anatomy (How Each Skill Works)

```
.claude/skills/[skill-name]/
├── SKILL.md          # YAML frontmatter + markdown process definition
├── scripts/          # Python scripts (one script = one job)
│   └── *.py          # Accept CLI args, return JSON to stdout
├── references/       # Supporting docs, configs
└── assets/           # Templates, fonts, icons (optional)
```

**SKILL.md frontmatter example:**
```yaml
---
name: research
description: Deep research on any topic. Use when user says "research X"
model: sonnet
context: fork
user-invocable: true
allowed-tools: Bash(python3 .claude/skills/research/scripts/*)
---
```

**Script contract:** Single responsibility. CLI args in, JSON to stdout, errors to stderr, exit 0 = success.

---

## Core Design Principles

### 1. Separation of Concerns
AI reasons about **what** to do. Deterministic Python scripts handle **how**.

```
All-AI approach:       90%^5 steps = 59% accuracy
Separation approach:   90% AI decision x 99.9% script execution = consistent
```

### 2. Model Routing for Cost
| Model | Use | Cost |
|---|---|---|
| Haiku | Simple tasks, formatting | ~$0.25/M tokens |
| Sonnet | Most pipelines, research, content | ~$3/M tokens |
| Opus | Complex reasoning, code review | ~$15/M tokens |

### 3. Skills > Prompts
Each workflow is a self-contained package (SKILL.md + scripts + references), not inline instructions.

### 4. Hooks > Prompt-Based Safety
Claude can be convinced to ignore prompt rules. Exit code 2 from a PreToolUse hook is a **deterministic block** that cannot be bypassed.

### 5. Python Scripts > MCP for Frequent Ops
MCP servers add ~15K tokens each to context. Direct API calls via Python scripts are cheaper for common operations.

---

## Tech Stack

### Core (Required)
- **Claude Code** — Primary IDE/harness ($20-200/month subscription)
- **Anthropic Claude API** — AI reasoning engine
- **Python 3.9+** — Script execution
- **SQLite** — Local structured data

### Optional Integrations
| Integration | Used By | Purpose |
|---|---|---|
| Telegram | telegram skill, Iris Core | Mobile bot access |
| Pinecone | memory skill | Vector database (~$0.04/month free tier) |
| mem0 | memory skill | Fact extraction + deduplication |
| OpenAI | mem0, research-lead | GPT-4.1 Nano for fact extraction |
| Perplexity | research-lead | Enhanced research synthesis |
| Gmail API | email-digest | Automated inbox processing |
| Slack | email-digest | Briefing notifications |
| Gamma | gamma-slides | Presentation generation |
| Google Sheets | research-lead | Lead storage |
| Astro + Tailwind + GSAP | build-website | Static site framework |
| Next.js/React + Supabase | build-app | Full-stack app framework |

---

## Deployment Models

### 1. Local Claude Code (Default)
User downloads Pro, opens in Claude Code, runs setup wizard. Everything runs locally.

### 2. Headless Mode (Automation)
```bash
claude -p "/weekly-review" --output-format json
```
Cron-scheduled skill execution without the IDE open.

### 3. Telegram Daemon (Mobile Access)
```bash
python3 .claude/skills/telegram/scripts/telegram_handler.py
```
Long-polls Telegram, invokes Claude headlessly, captures to memory.

### 4. VPS (Iris Core only)
Hostinger VPS with systemd service. ~$15-20/month at 100 daily active users.

---

## Current State Summary

**What's built and working:**
- Full 18-skill suite with scripts and references
- 3 specialized agents with model routing
- 3-tier memory system (tiers 1+2 working, tier 3 optional)
- Hook-based safety guardrails and memory capture
- Setup wizard (iris-setup) for first-run configuration
- Landing page with 4-tier pricing
- Iris Core Telegram bot (standalone product)
- AI OS Template (open-source MIT version)
- Comprehensive documentation (ARCHITECTURE.md, skill guides, upgrade paths)

**What's in progress / gaps:**
- No analytics dashboard (directory exists but empty)
- No automated test suite
- No formal pricing numbers documented
- No Core-to-Pro migration path documented
- Single-user only (no multi-user support)
- No web UI (all interaction through Claude Code IDE)
- No data backup/restore utilities
- English only (no localization)
- No performance benchmarks documented

---

## Git History

```
6fe58e5  Add remaining landing page files (images, preorder, old version)
8fdc73b  Fix check-in scheduler: support relative time extraction
f3461d6  Merge PR: Add Iris landing page with updated 4-tier pricing
405e675  Add Iris landing page with updated 4-tier pricing structure
2041463  Initial commit: Iris Core + Iris Pro + supporting files
```

---

## Cost Estimates

| Component | Monthly Cost |
|---|---|
| Claude Code subscription | $20-200 |
| Anthropic API (moderate use) | $5-50 |
| Pinecone (free tier, 100K vectors) | ~$0.04 |
| OpenAI for mem0 (GPT-4.1 Nano) | ~$1-5 |
| Lead research pipeline | ~$0.40/lead |
| **Total (starter)** | **~$25-55** |
| **Total (power user)** | **~$100-300** |

---

*This document covers the full Iris Pro build as of April 2026. Use it to onboard collaborators, brief other AIs, or plan next steps.*
