# IRIS Project Tracker

> Last updated: 2026-04-09

---

## In Progress

- [ ] **Accountability engine tuning** — Engine wired to Telegram + 5 scheduled tasks created, needs real user testing to calibrate thresholds `#accountability` (added 2026-04-05)
- [ ] **Iris Core VPS hardening** — Bot deployed and running, needs monitoring and edge case handling for multi-user load `#core` (added 2026-04-05)
- [ ] **Onboarding flow polish** — Setup wizard skill exists, needs end-to-end testing with a fresh user `#onboarding` (added 2026-04-05)
- [ ] **Memory system activation** — Tier 3 (Upstash Vector + mem0) built but needs API keys configured and tested `#memory` (added 2026-04-05)

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
