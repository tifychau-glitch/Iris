# AI OS

> Turn Claude Code into your AI business operating system.

A free, open-source template that transforms a Claude Code workspace into a structured operating system for your business. Clone it, run the setup wizard, and get a system that knows your business, writes in your voice, researches for you, manages your tasks, and grows with you.

## Quick Start

1. Unzip the template
2. Open the folder in Claude Code
3. Say anything — IRIS takes it from there

## What's Inside

### 25 Skills (Your Programs)

**Starter Skills (zero config):**

| Skill | What It Does |
|-------|-------------|
| `iris-setup` | Setup wizard — configures the system for your business |
| `research` | Deep research on any topic using web search |
| `content-writer` | Create content in your voice (LinkedIn, email, blog) |
| `meeting-prep` | Research + talking points for upcoming meetings |
| `email-assistant` | Triage emails, draft responses, summarize threads |
| `weekly-review` | Structured weekly review and next-week planning |
| `task-manager` | SQLite-backed task and project tracking |
| `skill-creator` | Create your own custom skills |

**Power Skills (optional API keys):**

| Skill | What It Does |
|-------|-------------|
| `research-lead` | LinkedIn URL → full research package + personalized outreach |
| `content-pipeline` | YouTube transcript → LinkedIn posts + carousel PDFs |
| `email-digest` | Automated inbox → sentiment analysis → Slack briefing |
| `gamma-slides` | Markdown → professional slide deck via Gamma |
| `build-website` | PRISM framework → premium static websites |
| `build-app` | ATLAS framework → full-stack applications |
| `memory` | mem0 + Upstash Vector — semantic search, auto-capture, dedup |
| `telegram` | Mobile access — message your AI assistant from your phone |
| `iris-accountability-engine` | Tracks commitments vs completions, dynamic accountability levels |
| `plugin-builder` | Package skills into distributable plugins |

### 3 Agents (Your Workers)

| Agent | Model | Purpose |
|-------|-------|---------|
| `researcher` | Sonnet | Read-only research tasks |
| `content-writer` | Sonnet | Content generation in your voice |
| `code-reviewer` | Opus | Code quality analysis |

### 3-Tier Memory

1. **MEMORY.md** — Always loaded. Your persistent brain.
2. **Daily logs** — Session history. What happened each day.
3. **Vector memory** (optional) — mem0 + Upstash Vector. Automatic fact extraction, semantic search, deduplication. ~$0.04/month.

### Hooks (Your Security)

- **Stop hook** — Auto-captures memories after every response
- **PreToolUse hook** — Blocks dangerous commands (rm -rf, force-push, etc.)
- **PostToolUse hook** — Validates script output

## Architecture

```
iris/
├── CLAUDE.md                    # Kernel (~80 lines)
├── install.sh                   # One-command setup
├── .claude/
│   ├── skills/                  # 25 skills (your programs)
│   ├── agents/                  # 3 subagents (your workers)
│   └── rules/                   # Modular system rules
├── context/                     # Your business + voice (filled by wizard)
├── args/                        # Runtime preferences
├── memory/                      # MEMORY.md + daily logs
├── data/                        # SQLite databases
│   └── hooks/                   # Automation hooks
└── docs/                        # Guides and upgrade paths
```

## The OS Analogy

| OS Concept | AI OS Equivalent |
|------------|-----------------|
| Kernel | CLAUDE.md — system instructions |
| Programs | Skills — auto-discovered workflows |
| Security | Hooks — guardrails and automation |
| Workers | Agents — specialized subprocesses |
| Filesystem | Context — business knowledge |
| Config | Args — runtime preferences |
| Memory | MEMORY.md + logs + vectors |
| Databases | SQLite in data/ |
| Cron | Headless mode scheduling |

## Requirements

- **Claude Code subscription** ($20-200/mo)
- **Python 3** — for scripts (most systems have this)
- **Anthropic API key** — for Iris to think
- **Upstash Vector** (free tier) — REST URL + token for long-term memory
- **Telegram** — so Iris can reach you

## Extending

### Create Custom Skills

```
"Create a skill for [describe your workflow]"
```

The skill-creator scaffolds everything for you. See [docs/SKILLS-GUIDE.md](docs/SKILLS-GUIDE.md).

### Add MCP Servers

Notion, Perplexity, Slack, YouTube — see [docs/MCP-SERVERS.md](docs/MCP-SERVERS.md).

### Automate with Cron

Schedule skills to run automatically — see [docs/AUTOMATION.md](docs/AUTOMATION.md).

### Upgrade Memory

Add vector memory with semantic search for ~$0.04/month — see [docs/MEMORY-UPGRADE.md](docs/MEMORY-UPGRADE.md).

## Philosophy

**Separation of concerns:** AI reasons about WHAT to do. Deterministic scripts handle HOW. This is why a 7-step pipeline produces consistent $0.40 results instead of probabilistic guessing.

**Skills, not prompts.** Every workflow is a self-contained package with instructions, scripts, and references. Auto-discovered, model-routed, isolated.

**Start simple, grow incrementally.** The core works with zero config. Add MCP servers, vector memory, automation, and custom skills as you need them.

## License

MIT — Free to use, modify, and distribute.

## Credits

Built by Tiffany Chau.
