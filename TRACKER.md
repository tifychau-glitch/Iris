# IRIS Project Tracker

> Last updated: 2026-04-12 (Phase 4 complete)

---

## In Progress

- [ ] **Accountability engine tuning** — Engine wired to Telegram + 5 scheduled tasks created, needs real user testing to calibrate thresholds `#accountability` (added 2026-04-05)
- [ ] **Iris Core VPS hardening** — Bot deployed and running, needs monitoring and edge case handling for multi-user load `#core` (added 2026-04-05)
- [ ] **Onboarding flow polish** — Setup wizard skill exists, needs end-to-end testing with a fresh user `#onboarding` (added 2026-04-05)
- [ ] **Connect real vault + run real compiler pass** — Set `IRIS_VAULT_PATH` in `.env`, open in Obsidian, fill in `me.md` + `my-business.md` with real content, let the silent-capture skills accumulate a week of data, then run compiler for real `#memory` `#accountability` (added 2026-04-09)

---

## Roadmap

### Phase 1 — MVP (Current)

- [ ] **Telegram Pro bot testing** — Handler built, needs real-world message flow testing `#telegram` (added 2026-04-05)
- [ ] **First 5 users onboarded** — Run real users through Core → Pro funnel `#launch` (added 2026-04-05)
- [x] **Context files populated** — my-business.md, my-voice.md filled with real content `#setup` (completed 2026-04-06)
- [ ] **Dashboard deployment** — Running locally at :5050, decide if it needs remote access `#dashboard` (added 2026-04-05)
- [ ] **Daily brief automation** — Skill exists, needs scheduled task configured to run mornings `#automation` (added 2026-04-05)
- [ ] **Email digest end-to-end** — Skill built, needs Gmail API credentials and first real run `#email` (added 2026-04-05)

### Phase 2 — After 10+ Users (Target: Late April 2026)

- [ ] **Single-user delegation tracking** — Extension of accountability engine, track tasks delegated to others `#accountability` (added 2026-04-04)
- [ ] **Dashboard commitment visualization** — Visual graphs of commitments vs completions over time `#dashboard` (added 2026-04-04)
- [ ] **Automated weekly pattern reports** — Weekly accountability summary delivered via Telegram `#telegram` (added 2026-04-04)
- [ ] **Core → Pro memory bridge** — When free user upgrades, carry Mt. Everest summary into Pro `#memory` (added 2026-04-05)

### Phase 3 — After Product-Market Fit (Target: June 2026)

- [ ] **Contextual GIF reactions** — IRIS sends relevant GIFs in Telegram for accountability moments `#telegram` (added 2026-04-04)
- [ ] **Life dashboard categories** — Health, personal, financial tracking beyond business `#dashboard` (added 2026-04-04)
- [ ] **Multi-channel notifications** — Slack + email + Telegram coordinated check-ins `#notifications` (added 2026-04-05)

### Obsidian Vault / AIOS Pivot (Phases 1-3a shipped 2026-04-09)

**Phase 3b — Dashboard review UI for compiler**
- [ ] **Dashboard Proposals page** — list pending proposals, approve/reject/apply buttons, status filters. Mirrors `review.py` CLI with better UX `#dashboard` `#memory` (added 2026-04-09)
- [ ] **Wire compiler run button** — dashboard action to trigger `compile.py --format json` and show the new proposals inline `#dashboard` `#memory` (added 2026-04-09)

**Phase 3c — Scheduled compiler runs**
- [ ] **Nightly compiler cron** — via scheduled-tasks skill, run `compile.py` at 11pm, count new proposals `#automation` `#memory` (added 2026-04-09)
- [ ] **Telegram surface** — if nightly run produces proposals, send "IRIS noticed N things overnight. Review?" via Telegram `#telegram` `#accountability` (added 2026-04-09)

**Phase 4 — Polish**
- [ ] **`me.md` linter** — warns on Claude-specific syntax, enforces model portability `#core` (added 2026-04-09)
- [ ] **Starter `Concepts/` examples** — seed new users with example synthesized articles `#onboarding` (added 2026-04-09)
- [ ] **Vault usage docs** — "How to use your vault with Iris" guide `#docs` `#onboarding` (added 2026-04-09)
- [ ] **Identity-edit proposals** — extend compiler to propose edits to `me.md`/`my-business.md` with diff preview + explicit confirm `#memory` (added 2026-04-09)

**Phase 5 — Scale (deferred until needed)**
- [ ] **FTS5 fallback search** — only when `index.md` navigation isn't enough `#memory` (added 2026-04-09)
- [ ] **Vector search layer** — optional, rare unstructured-query edge case `#memory` (added 2026-04-09)
- [ ] **File watchers / staleness handling** — only if the semantic layer gets added `#automation` (added 2026-04-09)

**Deprecation (after Phase 3 stable + real usage data)**
- [ ] **Migrate existing mem0 data** — one-shot export to `vault/imported/`, curate manually `#memory` `#cleanup` (added 2026-04-09)
- [ ] **Remove `mem0` skill** `#cleanup` (added 2026-04-09)
- [ ] **Remove Upstash Vector config** `#cleanup` (added 2026-04-09)
- [ ] **Deprecate Pinecone connector** — already optional, mark as legacy `#cleanup` (added 2026-04-09)
- [ ] **Rewrite `auto_capture.py`** — redirect from mem0 → Iris Journal + vault `#memory` `#core` (added 2026-04-09)

---

## Known Bugs

- [ ] **research-lead DM quality review disabled** — Rubric doesn't match dm_sequence behavior, needs update before re-enabling `#skills` (found 2026-04-05)
- [x] **tasks.db empty / not connected** — Wired: task-sync scheduled task pulls tasks.db → accountability commitments daily at 7 AM `#data` (resolved 2026-04-06)
- [x] **iris_accountability.db empty** — Wired: Telegram handler calls get_level + log_interaction, 5 scheduled tasks automate the full loop `#accountability` (resolved 2026-04-06)
- [x] **Duplicate skill directories** — Old `claude/` excluded via `.claudeignore`, `.claude/skills/` is canonical `#cleanup` (resolved 2026-04-06)
- [ ] **Iris Core conversation memory resets on restart** — In-memory Python dict lost when bot process restarts on VPS `#core` (found 2026-04-05)

---

## Ideas & Considerations

> Not committed. Showed interest, worth revisiting. No timeline.

- [ ] **"Starter vault" onboarding path** — for users who've never used Obsidian. Auto-creates vault folder, walks through Obsidian install, drags it into dashboard. Second track alongside "Connect existing vault" `#onboarding` (added 2026-04-09)
- [ ] **Compiler review via Telegram** — batch proposal approvals in Telegram instead of (or in addition to) dashboard. Might drive higher engagement `#accountability` `#telegram` (added 2026-04-09)
- [ ] **`me.md` linter — warning or hard block?** — decide how strictly to enforce model portability in user-written identity files `#core` (added 2026-04-09)
- [ ] **Marketing positioning: AIOS-native vs standalone** — pick a lane before Phase 4 onboarding polish. Tradeoff: narrower ICP + stronger narrative vs broader reach + weaker differentiation `#launch` `#marketing` (added 2026-04-09)
- [ ] **Observation → vault proposal loop** — Iris notices a pattern (e.g. repeated word usage) → proposes adding to `me.md` → user approves. Preserves "Iris learns you" magic without violating user ownership `#accountability` `#memory` (added 2026-04-09)
- [ ] **Behavioral vs aspirational gap surfacing** — user writes aspirationally in vault, behaves differently in journal. Iris should explicitly name this gap in check-ins — core accountability signal `#accountability` (added 2026-04-09)
- [ ] **White label licensing** — Architecture already supports it, could license IRIS to other coaches `#business` (added 2026-04-04)
- [ ] **IRIS API** — Accountability-as-a-service for other platforms `#business` (added 2026-04-04)
- [ ] **Financial stakes tracking** — Legal complexity, consider Beeminder partnership instead of building `#accountability` (added 2026-04-04)
- [ ] **IRIS Pods** — Cross-user accountability groups, needs multi-tenant infrastructure `#social` (added 2026-04-04)
- [ ] **Auto-documentation / SOP generation** — Screen recording approach is a separate product `#automation` (added 2026-04-04)
- [ ] **Meme generator** — GIF reactions (Phase 3) probably covers this, may not need standalone `#fun` (added 2026-04-04)
- [ ] **Voice mode** — IRIS responds with voice notes in Telegram, more personal `#telegram` (added 2026-04-05)
- [ ] **Mobile companion app** — Native app vs Telegram-only, Telegram is probably enough for now `#mobile` (added 2026-04-05)
- [ ] **Stripe integration** — Payment processing for Pro tier, needed before public launch `#business` (added 2026-04-05)
- [ ] **Referral system** — Users refer others to Core, get Pro credits `#growth` (added 2026-04-05)

---

## Recently Completed

- [x] **Memory Phase 5: Response Behavior + Memory Usage Policy** — `memory-usage-policy.md` behavioral rules loaded every session: 4-mode decision matrix (silent/cite/confirm/ignore), stale-awareness thresholds, pattern surfacing rules (3+ instances, not emotional, max 1 per session), citation style by memory type (Core State fresh → state cleanly, stale → date-anchored question, wiki → working understanding, inferred → never cite). Anti-pattern list prevents memory creep, robotic phrasing, and accountability surfacing during venting. `response_policy.py` with `decide_usage_mode()`, `citation_phrase()`, `should_surface_pattern()` functions. 20/20 golden scenario tests green `#memory` `#core` (completed 2026-04-12)
- [x] **Memory Phase 4: Retrieval Ranking** — `ranking.py` module with trust priors by layer/source, field-sensitive freshness profiles (pricing 7-day, commitments 5-day, identity no decay), source bonus to prevent semantic relevance overriding trust for canonical questions, query-type detection (canonical/pattern/history/general), confidence labels grounded in trust+freshness not raw score. Wired into `tiered_search()` in `smart_search.py`. Pending writes filtered before ranking. 20/20 golden tests green. Canonical queries return Core State with `query_type: canonical` and `High` confidence label `#memory` `#core` (completed 2026-04-12)
- [x] **Memory Phase 3: Ingest Pipeline** — `ingest.py` classify-and-route pipeline with 3-stage separation (is_memory_worthy → classify → promote). 7 routing classes: canonical_fact, preference, current_state, project_context, reference_knowledge, retrieval_only, noise. Retrieval signals pre-checked before field signals to prevent meeting notes triggering Core State. Meta-observation prefixes route to wiki even when mentioning canonical entities. Emotion patterns drop in Stage 1. Inferred sources block at Stage 3. Plugs into Phase 2 `queue_write()` — field policies apply. 30-example golden test set 30/30 green. Logs to `ingest-log.jsonl`, review items to `ingest-queue.jsonl` `#memory` `#core` (completed 2026-04-12)
- [x] **Memory Phase 2: Controlled Promotion + Write Governance** — `field-policies.json` per-field write rules (confirmation_policy enum, nullable staleness_days, confidence_minimum). `pending-writes.jsonl` review queue with full metadata (current_value, evidence, confidence, actor). 5-gate write enforcement in `core_state.py` (source → field policy → confirmation → confidence → execute). All dispositions logged to audit (accepted/rejected/blocked_by_policy/queued/stale_flag). Deterministic MEMORY.md projection rebuild via `--project`. Test-verified: system_canonical blocked from offer_stack, low-confidence write queued, approve flow executes write with user_confirmed source `#memory` `#core` (completed 2026-04-12)
- [x] **Memory Phase 1: Core State foundation** — `core-state.json` canonical facts (identity, goals, pricing, tone, commitments, active project). `core-state.schema.json` JSON Schema validation. `core_state.py` with lookup/write/update/validate/matches/context CLI. `audit-log.jsonl` append-only write history. `memory-protocol.md` updated with source-of-truth hierarchy (core-state > MEMORY.md > daily logs). Pinecone replaces Upstash in `mem0_config.yaml` + `.env.example`. `MEMORY-SPEC.md` 12-section architecture spec `#memory` `#core` (completed 2026-04-12)
- [x] **Landing page redesign: single-tier premium positioning** — Replaced 4-tier model with single Iris ($1,497 one-time). Founder-focused audience targeting. Core strategy: pattern detection system ("she sees the gap between what you say and do"). Credentials from mechanism specificity + founder lived experience + 30-day guarantee, not testimonials. Sections redesigned: founder story (Why I Built This), pain mirror (visibility insight), pricing (cost-of-inaction anchored), features (mechanism-focused), FAQ (7 founder objections), CTA (calm/confident), footer (observer positioning). Tone consistent, repetition reinforcing, audience narrowing intentional. Critical pass complete: conversion-ready with optional refinement (trim 1-2 pricing sentences). 3 commits. `#marketing` `#landing-page` (completed 2026-04-11)
- [x] **Phase 3a: Compiler skill MVP shipped** — `compile.py` reads journal (via iris-journal subprocess) + vault identity, calls LLM via `ai_provider`, stores proposals in `data/compiler_proposals.db`. `review.py` CLI handles list/show/approve/reject/apply. Types: `new_concept`, `append_to_effort`, `observation`. Trust contract enforced at 3 layers. Validated end-to-end with real LLM — produced "Real-Person Gate" concept from 7 synthetic friction entries, correctly cited journal + vault sources `#memory` `#accountability` `#skills` (completed 2026-04-09)
- [x] **Phase 2: vault_context.py + IRIS.md startup instructions** — IRIS reads `index.md` + 4 identity files + `maps/iris-rules.md` + most recent Calendar entry at every returning-user conversation. Graceful fallback when vault not configured. No hook — explicit invocation documented in IRIS.md `#memory` `#core` (completed 2026-04-09)
- [x] **Phase 1: Obsidian vault foundation** — `vault` skill with `vault_lib.py` (read/write/append-to-section/list), `vault_init.py` (scaffold), `vault_read.py`/`vault_write.py` (CLI). 8 starter templates with guidance prompts. Dashboard "Obsidian Vault" connector card. `CLAUDE.md` → `IRIS.md` rename with 1-line pointer. 5 `_find_project_root()` sentinels updated. Path traversal blocked, append-only trust contract, symlink escapes caught `#memory` `#dashboard` `#onboarding` (completed 2026-04-09)
- [x] **Architecture pivot to Obsidian vault + markdown-first memory** — 9 locked decisions: no git, two-layer raw/compiled model, `index.md` navigation over search, Iris Journal separate from vault, portable identity files, `CLAUDE.md` → `IRIS.md` rename, append-only reserved sections, retrieval degradation path (direct → grep → FTS5 → vectors), user owns everything. Full context in `memory/logs/2026-04-09.md` `#core` `#memory` (completed 2026-04-09)
- [x] **5 silent-capture accountability skills shipped** — friction-log, goal-decay-tracker, honest-recommit, energy-mapping, iris-journal. Consent-scoped, threshold-gated, no receipts-style lists `#accountability` `#skills` (completed 2026-04-09)
- [x] **IRIS Journal** — Read-only unified view across all silent-capture skills. Zero new storage, computes state at read time `#accountability` (completed 2026-04-09)
- [x] **email-digest migrated to Telegram** — Swapped Slack for Telegram delivery, added Claude sentiment pass `#email` `#telegram` (completed 2026-04-09)
- [x] **Dashboard Build Log feature** — /build-log route, API endpoint, new page, IRIS-BUILD-LOG.md living record, session-log backfill script `#dashboard` (completed 2026-04-09)
- [x] **Architecture HTMLs moved to iris-brain** — iris-architecture, iris-diagram, iris-system-map relocated to canonical home `#docs` `#cleanup` (completed 2026-04-09)
- [x] **CLAUDE.md overhaul** — Trimmed from 404 → 242 lines. Leaner handbook, same identity + voice + operating rules `#core` `#docs` (completed 2026-04-09)
- [x] **Accountability engine wired to Telegram** — telegram_handler.py calls get_level + log_interaction, accountability context injected into every response `#accountability` (completed 2026-04-06)
- [x] **5 accountability scheduled tasks** — followup (30min), ghost detector (6h), EOD summary (9PM), missed tasks (11:55PM), task sync (7AM) `#automation` (completed 2026-04-06)
- [x] **Post-changes audit + fixes** — Comprehensive audit: fixed skill counts (25), setup.sh→install.sh refs, dead code, Telegram whitelist gap, Upstash made optional, car-wash hardcoded paths, stale TRACKER entries `#cleanup` (completed 2026-04-06)
- [x] **Password hashing upgraded** — PBKDF2-SHA256 with 260K iterations in dashboard `#security` (completed 2026-04-06)
- [x] **.env quoting fixed** — Values now written as `KEY="escaped_value"` with proper escaping `#security` (completed 2026-04-06)
- [x] **Disconnect clears .env** — `remove_env_value()` called on connector disconnect `#dashboard` (completed 2026-04-06)
- [x] **.env file locking** — `fcntl.flock()` exclusive lock on all .env writes `#security` (completed 2026-04-06)
- [x] **Anthropic connector added** — Full entry in connectors.yaml with key validation `#dashboard` (completed 2026-04-06)
- [x] **Greeting loop detection** — telegram_handler.py detects repeated messages, redirects after 3 `#telegram` (completed 2026-04-06)
- [x] **Memory client graceful degradation** — Returns None on init failure, callers handle it `#memory` (completed 2026-04-06)
- [x] **Telegram test validates whitelist** — test_telegram.py checks user ID + sends test message `#telegram` (completed 2026-04-06)
- [x] **Input validation for garbage** — telegram_handler.py skips memory capture for typos/test input `#telegram` (completed 2026-04-06)
- [x] **Setup resume support** — iris-setup SKILL.md checks partial progress, offers to resume `#onboarding` (completed 2026-04-06)
- [x] **Dashboard startup validation** — init_db() failure now exits with error instead of continuing `#dashboard` (completed 2026-04-06)
- [x] **IRIS personality overhaul** — Rewrote CLAUDE.md with full voice, humor calibration, decision loops `#core` (completed 2026-04-05)
- [x] **Architecture visualization** — Built iris-architecture.html and iris-system-map.html with live build status `#docs` (completed 2026-04-05)
- [x] **Architecture visual update** — Updated both HTML files with MCP connectors, accurate skill counts, Flow 3 `#docs` (completed 2026-04-05)
- [x] **Visual auto-update rule** — Created .claude/rules/visual-updates.md for ongoing accuracy `#rules` (completed 2026-04-05)
- [x] **25 skills built** — Full skill library: research, content, email, telegram, accountability, build tools, and more `#skills` (completed 2026-04-05)
- [x] **3 subagents configured** — Researcher (Sonnet), content-writer (Sonnet), code-reviewer (Opus) `#agents` (completed 2026-04-05)
- [x] **7 MCP connectors active** — Gmail, Google Calendar, Slack, Canva, Chrome, Preview, Scheduled Tasks `#integrations` (completed 2026-04-05)
- [x] **3-tier memory system** — MEMORY.md + daily logs + Upstash Vector (Tier 3 needs keys) `#memory` (completed 2026-04-05)
- [x] **Dashboard web app** — Flask @ :5050 with Kanban board, settings, auth, connectors, API routes `#dashboard` (completed 2026-04-05)
- [x] **Security hooks** — Guardrail check (PreToolUse), output validation (PostToolUse), memory capture (Stop) `#security` (completed 2026-04-05)
- [x] **Iris Core deployed** — Telegram bot + web signup + Mt. Everest engine + email sender on Hostinger VPS `#core` (completed 2026-04-04)
- [x] **Landing page** — iris-ai.co with 4-tier pricing structure `#marketing` (completed 2026-04-04)
- [x] **Accountability engine** — 5-level system (Sweet → Brutal), tracks commitments vs completions `#accountability` (completed 2026-04-04)
- [x] **AI provider abstraction** — lib/ai_provider.py supports Claude Code CLI and direct API fallback `#infra` (completed 2026-04-04)
- [x] **Project tracker created** — This file + auto-update rule + dashboard seeding `#tracking` (completed 2026-04-05)

---

## How This Tracker Works

**Auto-updated by IRIS** during every work session per `.claude/rules/tracker-updates.md`.

**Item format:**
```
- [ ] **Title** — description `#tag` (added/found YYYY-MM-DD)
- [x] **Title** — description `#tag` (completed YYYY-MM-DD)
```

**Sections:**
| Section | What goes here |
|---------|---------------|
| In Progress | Actively being worked on right now |
| Roadmap | Committed work, organized by phase |
| Known Bugs | Broken things that need fixing |
| Ideas | Interesting but not committed — don't lose these |
| Recently Completed | Last 20 items done (older archived to daily logs) |

**Tags:** `#core` `#dashboard` `#telegram` `#memory` `#accountability` `#skills` `#automation` `#business` `#docs` `#cleanup` `#launch` `#integrations`
