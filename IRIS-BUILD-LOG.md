# IRIS Build Log

Living record of actions taken and questions asked while building IRIS.

This file is the source of truth. The dashboard page at `/build-log` renders it.

**Entry format:**
```
## [ACTION|QUESTION] YYYY-MM-DD — Short title
Body text. For questions, use **Q:** and **A:** lines.
```

Entries are newest-first within each section. New entries get appended to the top of the relevant section.

---

## Actions

## [ACTION] 2026-04-11 — Landing page complete: single-tier $1,497 premium positioning
Completed comprehensive refinement of iris-landing-page for founder/solopreneur audience targeting. Transitioned from 4-tier model ($99/$797/$1,497/Enterprise) to single-tier Iris ($1,497 one-time). Refined positioning strategy from "AI accountability tool" to "pattern detection system that closes the gap between what you say and what you do." Core methodology: credentials established through founder lived experience + mechanism specificity + 30-day guarantee, not testimonials. Updated 9 major sections: (1) Founder story reframed as "Why I Built This" focusing on pattern-blindness problem, not personal catharsis; (2) Pain mirror added explicit line about visibility gap; (3) Pricing section replaced with single-tier model anchored to "cost of inaction" framing; (4) Features tightened to mechanism-focused language ("reveals the gap," "detects patterns," "makes priorities visible"); (5) 30-day guarantee reframed from subjective "follow-through change" to objective "pattern detection works"; (6) FAQ replaced with 7 founder-specific objections (vs 12 generic questions), each killing a real concern; (7) Final CTA simplified to calm, confident founder language; (8) Footer reframed from "accountability coach" to "observer/witness to gap"; (9) Pronouns changed from "it" to "she" throughout. Tone consistency verified across all sections: sharp, observant, founder-focused, zero hype. Repetition analysis: "say vs. do" appears ~8x (intentional reinforcement), "pattern" appears ~6x (reinforcing, not redundant). Audience narrowing confirmed as intentional (self-directed founders, not support-seekers). Critical findings: page ready for conversion. Optional refinement: trim 1-2 sentences from pricing value frame to reduce say/do repetition. Commits: 3 total — pricing model implementation, FAQ + CTA refinement, footer update.

## [ACTION] 2026-04-10 — Onboarding walkthrough: identified vault gap
Ran through the full iris-setup onboarding flow as a first-time user simulation. Confirmed the 5-phase flow (Goals → Business → Voice → Tools → Auto-Configure) reads well conversationally. Identified a concrete gap: Obsidian vault setup has zero touchpoint during onboarding — new users finish Phase 5, see the capabilities list, and the vault exists only as an undiscovered feature. Natural insertion point: right after Phase 5 closes, before "What needs to get done first?" Proposed language and flow. Decision pending on whether to wire it in.

## [ACTION] 2026-04-09 — Phase 3a: Compiler skill (raw → compiled knowledge promotion)
Built `.claude/skills/compiler/` — the Karpathy compiler-analogy piece. `compile.py` reads journal data via subprocess to `iris-journal/scripts/journal.py`, reads vault identity via `vault_lib`, builds a system + user prompt, calls LLM through `lib/ai_provider.ai.reason()`, parses JSON proposals, stores them in `data/compiler_proposals.db` as `pending`. `review.py` CLI handles `list/show/approve/reject/apply` subcommands. Three proposal types: `new_concept` (creates `Concepts/<slug>.md`), `append_to_effort` (appends under reserved section in `Efforts/<file>.md`), `observation` (review-only flag for aspiration vs behavior gaps). Trust contract enforced at three layers — system prompt forbids identity edits, `review.py` hard-rejects writes outside `Concepts/` and `Efforts/`, `vault_lib.write_file()` refuses overwrite by default. Validated end-to-end with a real LLM call: seeded 7 synthetic friction entries about beta onboarding + investor email, plus filled-in `me.md` and `my-business.md`. Real LLM produced a `new_concept` ("Real-Person Gate") that named a structural pattern across 5 entries with different friction categories but a shared property — output goes to a real person — and an `observation` cross-referencing `my-business.md` Q2 priorities against the journal. Approved both, applied both, concept file landed in vault via `vault_lib`. Mock-LLM mode (`--mock-llm`) lets you smoke-test the storage/review flow without hitting an API.

## [ACTION] 2026-04-09 — Phase 2: vault_context.py + IRIS.md startup instructions
Built `vault_context.py` — single script that loads `index.md` + `me.md` + `my-everest.md` + `my-business.md` + `my-voice.md` + `maps/iris-rules.md` + the most recent `Calendar/YYYY-MM-DD.md` from the vault and returns formatted markdown (or JSON via `--format json`). Handles missing vault gracefully — returns `not_configured` or `path_missing` status, exits 0. Updated IRIS.md with a new "Vault Context" section telling IRIS to run this at the start of every returning-user conversation. Documents the read order, how to use each file, and the write contract (never edit user content, only append to reserved sections, never touch identity files without explicit confirmation). Also documents coexistence with `context/` files — vault preferred when connected, `context/` still works for backward compatibility. Chose explicit invocation over a SessionStart hook — transparent (user can see in IRIS.md exactly what IRIS is loading), no hook config to maintain. Smoke tests pass for all four states: not configured, configured + populated, formatted markdown output, and continuity (most recent calendar correctly picked).

## [ACTION] 2026-04-09 — Phase 1: Obsidian vault foundation (vault skill + dashboard card)
Built `.claude/skills/vault/` with `vault_lib.py` (shared helpers: read/write/append-to-section/list, path traversal blocked, overwrite refused by default, symlink escapes caught via `relative_to()` containment), `vault_init.py` (scaffolds starter vault into any folder, refuses to scaffold into folders containing existing `.md` files unless `--force`), `vault_read.py`/`vault_write.py` (CLI wrappers). Wrote 8 starter templates: `me.md`, `my-everest.md`, `my-voice.md`, `my-business.md`, `index.md`, `README.md`, `maps/vault-map.md`, `maps/iris-rules.md`, all pre-filled with HTML-comment guidance prompts. Added "Obsidian Vault" connector card to dashboard via `connectors.yaml` entry + `dashboard/scripts/test_obsidian_vault.py` — zero HTML changes needed. Test script handles scaffold-or-connect logic: if path is empty/missing it scaffolds, if path has existing `.md` files it connects. Default location `~/Documents/Iris Vault` so the user can leave the field blank. End-to-end verified: scaffolding works, reserved-section append works in 3 cases (empty file, heading at end, heading in middle of file with user content on both sides), path traversal rejected, overwrite refused, dashboard YAML validates and the dashboard boots cleanly with the new connector.

## [ACTION] 2026-04-09 — Rename CLAUDE.md → IRIS.md (model portability)
Copied the 242-line handbook from `CLAUDE.md` to a new `IRIS.md`, replaced `CLAUDE.md` with a 1-line pointer (`See [IRIS.md](IRIS.md) for the complete IRIS system handbook.`). Claude Code still auto-loads via the pointer file. Updated 5 scripts that use `_find_project_root()` to accept `IRIS.md` as a sentinel alongside `CLAUDE.md` (`mem0_client.py`, `telegram_handler.py`, `telegram_bot.py`, `telegram_send.py`, `message_db.py`) — belt and suspenders, pointer satisfies the check today, IRIS.md works if pointer is ever deleted. Updated `iris-setup/SKILL.md` line 21 and `README.md` lines 69, 87 to reference IRIS.md. Regression tests pass — iris-journal and telegram modules still resolve project root correctly.

## [ACTION] 2026-04-09 — Architecture pivot decision: vault-backed memory model
Locked in 9 architectural decisions during a long design session: (1) plain markdown files in a user-owned Obsidian vault, no git, direct local filesystem access; (2) two-layer architecture — raw layer (Iris Journal, append-only) + compiled layer (vault, curated, with a compiler that promotes raw → compiled); (3) `index.md` as primary retrieval mechanism, not search; (4) Iris Journal stays separate from the vault (clean ownership boundary); (5) identity files (`me.md`/`my-everest.md`/`my-voice.md`/`my-business.md`) are plain markdown, model-portable, owned by the user forever; (6) rename `CLAUDE.md` → `IRIS.md` for model portability; (7) append-only to reserved sections as the trust contract; (8) retrieval degradation path: direct reads → grep → FTS5 → vectors, only upgrade when previous tier stops working; (9) user owns everything — if IRIS or Claude disappear tomorrow, the vault still works. Driven by Karpathy's LLM Knowledge Bases framework + a follow-up video applying it to internal session data. Positioning shift: IRIS is no longer "an accountability app with better memory" — it's "the accountability layer for the user's AIOS (AI Operating System)."

## [ACTION] 2026-04-09 — Backfill Build Log from all Iris session history
Wrote `scripts/backfill_build_log.py` to walk every `.jsonl` file across all 7 Iris-related Claude Code project folders (Iris-Pro, Iris-Pro-2, Iris-Core, iris-landing-page, iris-product, Iris-AI-OS-Template, and the parent IRIS folder). Extracted 493 user messages and 830 assistant actions across 80 sessions, filtered out scheduled-task noise and read-only operations, then distilled into ~40 tight entries covering the real build history from March 25 to today.

## [ACTION] 2026-04-09 — Add Day/Week/Month/All views + calendar grid to Build Log
Added a Google Calendar-style view toggle to `/build-log`. Day shows a single day's entries, Week groups entries by day across the week, Month renders a calendar grid with entry count badges (click a day to drill down). Search is global — it bypasses date filtering so you can type "pinecone" or "landing page" and see every related entry regardless of view. Date nav (◀ label ▶) auto-hides when not needed.

## [ACTION] 2026-04-09 — Create IRIS Build Log system
Set up `IRIS-BUILD-LOG.md` as the source of truth for every action and question during the IRIS build. Added a new `/build-log` page to the dashboard with Actions / Questions tabs, search, and chronological view. IRIS writes entries inline as conversations happen; a wrap-up sweep catches anything missed before sessions close.

## [ACTION] 2026-04-08 — Refine CLAUDE.md onboarding: less linear, more natural
Rewrote the onboarding flow in CLAUDE.md based on feedback from Claude Chat review. First conversation is now adaptive and conversational instead of a rigid template — IRIS leads with attention, not a form.

## [ACTION] 2026-04-07 — Swap Upstash Vector for Pinecone
Replaced Upstash Vector with Pinecone as the optional long-term memory connector. Pinecone is free to start and gives cross-session memory. Decision driven by wanting users to own their own data without Tiffany holding a shared key for everyone.

## [ACTION] 2026-04-07 — Add iris-brain personal tooling
Built `/IRIS/iris-brain/` — a personal script that compiles current IRIS state (voice, business, architecture, memory) into a single context package for the Claude.ai Project knowledge base. Lets Tiffany brainstorm with Claude Chat at lower cost while keeping Iris-Pro as the build environment.

## [ACTION] 2026-04-07 — Add lib/ai_provider and test scripts
Provider abstraction layer so scripts can swap between Claude, OpenAI, and Gemini via `preferences.yaml` — one-line config change to switch LLMs without touching skill code.

## [ACTION] 2026-04-07 — Architecture visualization HTML and audit doc
Created `iris-architecture.html` and `iris-system-map.html` — visual component inventory with build status indicators (green/yellow/gray dots). Also added the system audit doc that catalogs every piece of the system and its current state.

## [ACTION] 2026-04-07 — Build visual diagram for explaining Iris to others
Created a clean diagram with minimal text for explaining the Iris setup to people who don't know the system. Addressed how Iris Core users connect through Claude subscription vs API key.

## [ACTION] 2026-04-07 — Context and memory setup
Populated `context/my-business.md`, `context/my-voice.md`, advisor files, and initial `MEMORY.md` entries with Tiffany's business details, voice, and goals.

## [ACTION] 2026-04-07 — Top-level docs, install scripts, launchers
Added `install.sh`, launcher scripts, and top-level documentation so the system can be set up from a clean machine.

## [ACTION] 2026-04-07 — Dashboard: auth, settings, connectors, scripts
Built the local dashboard at `localhost:5050` with login, Settings page, connector management (Gmail, Slack, Pinecone, Telegram, etc.), and script runners.

## [ACTION] 2026-04-07 — Add skills: advisor-council, constraint-finder, fact-check, session-wrap
Four new skills added to `.claude/skills/`.

## [ACTION] 2026-04-07 — Iris-Core: bot overhaul, replace scheduler, add email and calendar
Overhauled the Telegram bot, replaced the old scheduler, added email and calendar integration to Iris-Core.

## [ACTION] 2026-04-07 — Cleanup: remove duplicate Iris-Pro/claude/ folder
Removed duplicate `.claude` folder inside Iris-Pro.

## [ACTION] 2026-04-07 — Cleanup: remove misplaced landing page files
Moved landing page files out of Iris-Pro, added build overview doc.

## [ACTION] 2026-04-06 — Add Greg Isenberg to advisor council
Created a Greg Isenberg advisor in the council using YouTube videos as source material (startup ideation focus). Second advisor after Alex Hormozi.

## [ACTION] 2026-04-06 — Hormozi advisor pricing strategy session
Big strategic session consulting the Hormozi advisor on the Iris Core → Iris Pro funnel and $797 price point. Refined the positioning around Iris Core as a lead magnet with a quick-win offer tied to Mount Everest.

## [ACTION] 2026-04-06 — Ship prep: credentials sprint + roadmap review
"Make Iris shippable by end of night" session. Walked through every connector that needed credentials, worked through the roadmap blockers.

## [ACTION] 2026-04-06 — First system audit + work through action items
Ran a full system audit of Iris, then worked through the action items one chunk at a time (3 items per pass).

## [ACTION] 2026-04-06 — Second system audit after changes
Post-change audit to verify the fixes held and nothing else was broken.

## [ACTION] 2026-04-06 — Automatic model routing via hook
Set up automatic model routing so Opus/Sonnet/Haiku get picked per message class without Tiffany having to type the model name. Preceded by a test session using `haiku:` / `sonnet:` prefixes.

## [ACTION] 2026-04-06 — Create fact-check skill for hallucination prevention
Built the `fact-check` skill after discussing best practices for catching AI hallucinations. Automatic verification workflow.

## [ACTION] 2026-04-06 — Reset identity: SaaS accountability AIOS through Telegram
Big reset conversation — clarified from scratch that Iris is an accountability AIOS users communicate with through Telegram. Sharpened the positioning after drift in prior sessions.

## [ACTION] 2026-04-06 — Create .claude.ignore to clean up folder
Generated `.claude.ignore` to exclude files that don't help Claude with the build.

## [ACTION] 2026-04-05 — Build TRACKER.md for Iris roadmap
Created the central task list / to-do list for Iris, with roadmap items, known bugs, recently completed, and ideas. Became the single source of truth for ongoing work.

## [ACTION] 2026-04-05 — Deploy visual overview on VPS
Deployed the visual system overview to the Hostinger VPS so Tiffany can view it from anywhere.

## [ACTION] 2026-04-05 — Design advisor council skill (inspired by "One" AIOS)
Reviewed Jimmy's "One" AIOS webinar transcript, pulled out the advisor council concept, designed the skill around calling specific advisors or a full panel. Laid groundwork for adding high-quality source material (books, transcripts) per advisor.

## [ACTION] 2026-04-05 — Initial system visualization v1
First cut of the visual representation showing Iris Pro, Iris Core, VPS, databases, and status of everything built. Later refined into the full architecture HTML.

## [ACTION] 2026-04-04 — Log new skill idea: market/news/social research skill
Captured a new skill idea during brainstorming: AI that does market research, social media research, and news research automatically. Parked for later.

## [ACTION] 2026-04-04 — Major architectural session: API key vs Claude Pro subscription
91-message session restructuring the whole Iris pricing/access model around Anthropic API keys vs users' Claude Pro subscriptions. Affected how Iris Core ships, how users pay, and how Telegram → agent messaging flows.

## [ACTION] 2026-04-04 — Set up scheduled project scanner (4x daily)
Daily scheduled task runs at 9am, 12pm, 3pm, 6pm to scan the Iris project and log what's been updated. Runs via Claude Code's scheduled-tasks MCP.

## [ACTION] 2026-04-03 — Integrate "One AIOS" webinar concepts into Iris plan
Reviewed notes from Jimmy's "One AIOS" release, pulled applicable patterns into the Iris build plan. 50 tool calls in this session — a big planning + execution pass.

## [ACTION] 2026-04-03 — Overhaul IRIS personality and repo structure
Major pass on IRIS's voice and tone in `CLAUDE.md`, plus repo restructuring.

## [ACTION] 2026-04-03 — Run through onboarding wizard end-to-end
Walked through the full iris-setup onboarding flow as a first-time user to validate the experience.

## [ACTION] 2026-04-02 — Add Iris landing page with 4-tier pricing
Updated landing page structure to reflect the 4-tier pricing model.

## [ACTION] 2026-04-02 — Fix check-in scheduler: relative time extraction
Bug fix: scheduler now correctly parses relative time phrases like "in 20 minutes."

## [ACTION] 2026-04-02 — Initial commit: Iris Core + Iris Pro
First commit of the full system.

## [ACTION] 2026-04-01 — Scan + consolidate Iris-Pro-2 folder
Read through everything in the Iris-Pro-2 folder to identify redundant files that could be consolidated or deleted. No deletions yet — just the audit.

## [ACTION] 2026-04-01 — Add Car Wash Evaluator skill to Iris Pro
Imported the Car Wash Evaluator skill (built separately) into Iris-Pro's `.claude/skills/` so the agent could use it for land/site evaluation.

## [ACTION] 2026-04-01 — Add dev server auto-detection to launch.json
Detect project's dev servers and save configurations to `.claude/launch.json` for one-click start.

---

## Questions

## [QUESTION] 2026-04-09 — Can we backfill the Build Log from every Iris session, not just git history?
**Q:** There's a ton of build info buried in the past Claude Code sessions. Can you go read through all of them and backfill the log with real questions and actions, not just what's in git?
**A:** Yes. Claude Code stores every session as a JSONL file in `~/.claude/projects/`. Found 80 sessions across 7 Iris folders (52MB+). Wrote a script to extract user messages and tool calls, filter noise, then synthesized ~40 tight entries covering the real build history. Target: turning points and decisions, not every "okay keep going" message.

## [QUESTION] 2026-04-09 — Does the build log need git commits to show entries?
**Q:** Does everything need to be saved to Git in order to show up on the build log?
**A:** No. The dashboard reads directly from `IRIS-BUILD-LOG.md` on disk — entries show up the moment they're written, no commit needed. Git was only used once for the initial backfill.

## [QUESTION] 2026-04-09 — If I archive a session, do I lose the build log entries from it?
**Q:** If I archive a conversation or session, will I lose that information from the project?
**A:** No. The build log is a real file on disk, not stored inside any Claude session. The only risk is if IRIS forgets to log something — so we added a wrap-up sweep: "wrap up," "that's it," or similar triggers a final pass to capture anything missed.

## [QUESTION] 2026-04-09 — How should we track every question and action during the IRIS build?
**Q:** I'm losing track of all the threads, updates, and things I've asked. I want a living document that auto-updates. Google-doc style, dashboard, or something else?
**A:** Hybrid. Markdown file (`IRIS-BUILD-LOG.md`) as the source of truth, plus a `/build-log` dashboard page with tabs, search, and chronological view. Gets the simplicity of a doc and the polish of a dashboard without picking one.

## [QUESTION] 2026-04-09 — What does "closing the conversation" mean for an auto-capture hook?
**Q:** If a session-end hook logs things automatically, when does it actually fire?
**A:** There isn't a reliable "session end" event in Claude Code. The closest thing is the `Stop` hook, which fires after every response. Decision: skip the hook — just do inline capture during the conversation. Fewer moving parts.

## [QUESTION] 2026-04-09 — Is a plain markdown file the best format?
**Q:** Is a markdown file efficient for the AI but also nice for me to read?
**A:** Alone, no — markdown gets ugly at length. Better: markdown source of truth + dashboard page that renders it with tabs and search.

## [QUESTION] 2026-04-09 — How flexible is LLM switching? Could I drag Iris Pro into Gemini?
**Q:** As it currently is, how much flexibility do I have if I want to change LLMs and use OpenAI or Gemini 3?
**A:** Scripts can already swap between Claude/OpenAI/Gemini via a one-line change in `preferences.yaml` thanks to the `lib/ai_provider` layer. But the main orchestrator has to be Claude because it's running inside Claude Code. If you dragged Iris-Pro into a different CLI, the skills and scripts would still work, but the conversational layer depends on Claude Code itself.

## [QUESTION] 2026-04-09 — Could Iris Core ship as a Claude Code skill + docs instead of a full app?
**Q:** What would it look like to offer a version of Iris that has all the accountability, Mt Everest, cron jobs, etc., as just a skill someone installs?
**A:** Core could ship as a Claude Code skill + guidance docs; Pro is the full system built on top. Architectural choice to revisit — parked on roadmap.

## [QUESTION] 2026-04-08 — What's the most streamlined path forward if cost wasn't a factor?
**Q:** Assuming cost isn't an issue, what's the most user-friendly version of what we're building? Could we get one-click OAuth for Calendar, Gmail, and Slack all at once?
**A:** Discussed tradeoffs. Decision: don't spend too much time on the build — prioritize easier accountability features we can ship faster over a perfect OAuth experience.

## [QUESTION] 2026-04-08 — What are the 7 MCP servers Iris Pro includes? Should we add more?
**Q:** When it says Iris Pro includes 7 MCP servers, are those my personal ones or are they baked into Pro? Should we connect more?
**A:** Clarified: the 7 are Gmail, GCal, Slack, Canva, Chrome, Preview, and Scheduled Tasks. Adding more has diminishing returns — too many MCPs means more context overhead. Keep the set intentional.

## [QUESTION] 2026-04-08 — Can a minimal Iris Core run on just Claude Pro + Telegram?
**Q:** Strip out everything AIOS-related from the codebase. What's left if Core is only Telegram bot + Mt Everest conversation + email summary? Can that minimal version run on Claude Pro + user's Telegram?
**A:** Yes — that's the direction for the leaner Core offering. Informs how the Core/Pro split works.

## [QUESTION] 2026-04-07 — Upstash shared memory vs users providing their own key — what's the cost at 100 users?
**Q:** With Upstash as shared vector memory, what would providing memory for ~100 users cost me? I'm doing a one-time charge, not recurring.
**A:** Cost math didn't work for a one-time payment model — recurring infrastructure costs would eventually outpace the upfront charge. Decision: switch from Upstash (shared) to Pinecone (user-provided). Users own their memory, Tiffany doesn't hold the shared cost.

## [QUESTION] 2026-04-06 — How does Iris Core's cloud-based Telegram connection actually work?
**Q:** Currently Iris Core uses a cloud-based Telegram connection. My own Iris is connected with my own API in a cloud — when people talk through Iris Core, how does that route?
**A:** Clarified the architecture: your bot token → cloud server → your API key → Claude → response. Users never see your credentials but the costs route through you. Informed the shift toward users bringing their own credentials in Pro.

## [QUESTION] 2026-04-06 — Can you handle code imports automatically instead of me copy-pasting into the terminal?
**Q:** A lot of the build requires me personally going to the CLI and importing code you give me. What would it take for you to just do that automatically?
**A:** Walked through the options (Claude Code's tool use is already doing this — most "import" steps are me running the Edit/Write tools directly). For things where Tiffany still has to copy-paste, identified which ones and reduced manual steps.

## [QUESTION] 2026-04-06 — How do I test pieces of IRIS without running the whole thing? I'm not a developer.
**Q:** What's the best way to test specific parts or processes in Iris without running the entire file? I don't read code well, so if it's a bunch of scripts I'll be lost.
**A:** Proposed a simpler approach: individual runnable scripts per skill with clear English-language output, plus a dashboard runner that kicks them off with one click. No code reading required.

## [QUESTION] 2026-04-06 — Best way to prevent AI hallucinations?
**Q:** What's the best way to prevent hallucinations when I ask AI for best practices or why something is a certain way? Can we build a skill that does fact-checking automatically?
**A:** Yes — led to building the `fact-check` skill that verifies claims in AI responses against sources.

## [QUESTION] 2026-04-06 — Do we have a system that orchestrates which model is used for what task?
**Q:** Currently do we have anything set up that orchestrates which model is used for what task?
**A:** Not automated at the time. Led to building the pre-hook that reads incoming messages and routes to Opus/Sonnet/Haiku based on task type, so Tiffany doesn't have to type the model name.

## [QUESTION] 2026-04-06 — Have we set up alternate LLM models as fallback?
**Q:** Have we set it up so we have alternate LLMs as fallback in case Claude is no longer the leader one day?
**A:** Yes — `lib/ai_provider` lets scripts swap between Claude, OpenAI, and Gemini via a one-line change in `preferences.yaml`. Captured in MEMORY.md.

## [QUESTION] 2026-04-04 — What are the implications of switching vector memory from Pinecone to Zilliz?
**Q:** What would it mean to switch from Pinecone to Zilliz? Price, build effort, etc.?
**A:** Walked through the tradeoffs. Decision at the time: stay with the current direction. (Later switched the question entirely — ended up at Pinecone after briefly going through Upstash.)

## [QUESTION] 2026-04-04 — How do we balance minimizing IRIS's token usage per message vs capability?
**Q:** I've been testing Iris Core and thinking about the balance between minimizing token usage per message and keeping her capable. Thoughts?
**A:** Discussed the tradeoffs — short responses save tokens but can feel cold. Led to the "tight by default but stretch for real moments" rule in the voice guide.

## [QUESTION] 2026-04-04 — Should we build specialized skills, or put everything into instructions?
**Q:** Should we build a whole bunch of Iris-specific skills, or build everything into her instructions? Would combining skills reduce overload from having too many to reference?
**A:** Skills win for anything repeatable — instructions for anything that needs context every time. Combining skills can help if they share overlapping reference material. No hard rule, decided case-by-case.

## [QUESTION] 2026-04-04 — Does my computer need to be on for the scheduled task to run?
**Q:** Since the scheduled project scanner runs locally, does my computer have to be on for it to run?
**A:** Yes if local, no if moved to a remote trigger. Discussed the tradeoffs — kept it local for now.

## [QUESTION] 2026-04-04 — API keys vs Claude Pro subscription — what's the right access model?
**Q:** I've been going back and forth on whether users should need an Anthropic API key or if Iris can work with their existing Claude Pro subscription. The way I was structuring it wasn't working.
**A:** Big architectural session. Decision path: Core on Claude Pro subscription (via Claude Code) for the lean offering, Pro users can bring their own API key for programmatic access. Reshaped how pricing tiers work.

## [QUESTION] 2026-04-01 — Car Wash skill: LoopNet upload or just address input?
**Q:** Am I able to upload a LoopNet listing to the Car Wash Evaluator skill, or do I just put in an address?
**A:** At the time, address-only. LoopNet PDF upload noted as a future enhancement.
