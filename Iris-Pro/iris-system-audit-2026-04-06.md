# Iris SaaS — Comprehensive System Audit

**Date:** 2026-04-06
**Scope:** Full product, onboarding, integrations, architecture

---

## CRITICAL BUGS (Block Product Launch)

### 1. ANTHROPIC_API_KEY marked as required but should be optional

**Category:** Integration

secure_key_input.py includes ANTHROPIC_API_KEY in REQUIRED_KEYS, but users can choose different AI providers (OpenAI, Google). This blocks --check-all for users with AI_PROVIDER != anthropic.

**Impact:** Onboarding fails for users not using Anthropic. Blocks product launch validation.

**File:** `.claude/skills/iris-setup/scripts/secure_key_input.py`

**Fix:** Move ANTHROPIC_API_KEY to OPTIONAL_KEYS if AI_PROVIDER is openai or google. Check provider first.

**Effort:** LOW

### 2. .env values written without quotes — breaks on spaces/special chars

**Category:** Data Integrity

dashboard/app.py writes KEY=value format. If value contains spaces, equals, or quotes, the file breaks. Security issue: keys with special chars become readable.

**Impact:** Credentials with special characters corrupt .env. Unencrypted API keys in plaintext.

**File:** `dashboard/app.py (write_env function)`

**Fix:** Quote all values: KEY="value". Use shlex.quote() or proper escaping.

**Effort:** LOW

### 3. Telegram bot whitelist empty after setup — bot rejects all messages

**Category:** Integration

User connects Telegram bot token successfully (test passes). Bot starts polling. But messaging.yaml has allowed_user_ids: []. Bot receives messages but rejects them silently. No error, no hint.

**Impact:** Critical dead-end. User thinks bot is broken. Most likely first thing new users hit.

**File:** `.claude/skills/telegram/references/messaging.yaml`

**Fix:** During onboarding, after Telegram token is saved, auto-populate whitelist with user's Telegram ID. Script: ask user to message @userinfobot, extract ID from dashboard.

**Effort:** MEDIUM

### 4. Disconnect doesn't clear .env — state mismatch

**Category:** State Management

User disconnects a connector in dashboard. DB updates, UI shows disconnected. But .env still has the old credentials. Memory script or Telegram handler might use stale keys.

**Impact:** Confusing behavior. Credentials that should be removed still work. Security issue: old keys aren't invalidated.

**File:** `dashboard/app.py (disconnect_connector)`

**Fix:** When user disconnects, remove key from .env AND update DB. Provide visual confirmation.

**Effort:** LOW

### 5. Telegram test only validates token, not whitelist or permissions

**Category:** Security

Telegram connector test only calls getMe (checks if token is valid). Doesn't check if whitelist is populated, doesn't send actual test message. Shows green checkmark but bot will reject all messages.

**Impact:** Users think integration is working when it's not. Major UX failure.

**File:** `dashboard/connectors/telegram.py (test method)`

**Fix:** Test should: 1) validate token, 2) check if whitelist is populated, 3) send actual test message to user, 4) fail if whitelist empty.

**Effort:** MEDIUM

---

## HIGH PRIORITY (Bad UX, Will Frustrate Users)

### 6. Greeting loop — 'hi' 5x with no graceful fallback

**Category:** UX

Saying 'hi' or 'hello' multiple times triggers IRIS to say hello back each time. No recognition that user is testing or stuck. No fallback after 2-3 attempts.

**Impact:** Users think bot is broken or dumb. Wastes time in initial impression.

**File:** `.claude/skills/telegram/scripts/telegram_handler.py`

**Fix:** Track repetition. After 2 identical messages, respond once and suggest: 'Type your goal or add a task.' Don't repeat.

**Effort:** LOW

### 7. No confirmation on unusual answers — 'Loophi' treated as gospel

**Category:** UX

User types 'Loophi' (clearly a typo/test). IRIS treats it as real input, logs it to memory, tries to work with it.

**Impact:** Garbage input corrupts user data and memory. Breaks accountability tracking.

**File:** `.claude/skills/iris-setup/SKILL.md (Phase 2 questions)`

**Fix:** On unusual inputs (1-3 letters, all caps, nonsense words), ask: 'Did you mean...?' or 'Confirm that's what you want me to remember.'

**Effort:** MEDIUM

### 8. No Anthropic connector in dashboard — users can't manage Anthropic key via UI

**Category:** Integration

connectors.yaml has entries for Telegram, Gmail, Slack, OpenAI, etc. Missing: Anthropic API key connector. Users with AI_PROVIDER=anthropic have no UI to set/rotate their key.

**Impact:** Users with Anthropic as primary must edit .env directly. Inconsistent UX.

**File:** `dashboard/connectors.yaml`

**Fix:** Add Anthropic API connector card. Validate key format (starts with sk-ant-). Test with getModels() call.

**Effort:** LOW

### 9. Race condition on .env writes — no file locking

**Category:** Concurrency

Dashboard, Telegram handler, memory scripts can all write .env simultaneously. No mutex/lock. One write can corrupt the file.

**Impact:** Occasional .env corruption. Hard to debug. Happens under load or during rapid integrations.

**File:** `All scripts that write .env`

**Fix:** Use fcntl.flock() (Unix) or filelock library. Acquire lock before write, release after.

**Effort:** MEDIUM

### 10. Memory client crashes at runtime — lazy initialization with bad creds

**Category:** Stability

Dashboard validates Upstash credentials at connection time. But mem0_client.py initializes lazily on first message. If credentials are wrong, bot crashes mid-conversation.

**Impact:** Users connect Upstash, think it's working, then bot crashes on first message. Bad first impression.

**File:** `.claude/skills/memory/scripts/mem0_client.py`

**Fix:** Test credentials at dashboard time, not runtime. Or provide better error message: 'Memory temporarily unavailable, continuing without it.'

**Effort:** MEDIUM

---

## MEDIUM PRIORITY (Polish Before Launch)

### 11. Dashboard startup fails silently — error in stderr, success message in stdout

**Category:** UX

init_db() fails (e.g., permissions), error printed to stderr. But 'Dashboard running' still prints. User thinks it's working.

**Impact:** Database not initialized. Skills crash when they try to access it.

**File:** `dashboard/app.py (main)`

**Fix:** Check init_db() return value. If fail, print error and exit(1). Don't continue.

**Effort:** LOW

### 12. Dashboard password hash is SHA-256 with 1 iteration — fine for dev, not SaaS

**Category:** Security

Password stored as sha256(password). No salt, no iterations. If leaked, can be brute-forced.

**Impact:** If dashboard is exposed to internet, passwords are vulnerable.

**File:** `dashboard/auth.py`

**Fix:** Use bcrypt or PBKDF2 with salt and 100K+ iterations. Or use argon2.

**Effort:** MEDIUM

### 13. Connector registry not synced after dashboard startup — new connectors won't appear until restart

**Category:** Configuration

connectors.yaml is read once on startup. New connectors added to YAML require dashboard restart to show up.

**Impact:** Users add new credentials, have to restart. Friction.

**File:** `dashboard/db.py (sync_connector_registry)`

**Fix:** Watch connectors.yaml for changes. Resync on file modification.

**Effort:** LOW

### 14. my-mteverest.md is empty — blocks goal-aligned accountability

**Category:** Feature

Template exists but user hasn't defined their Mount Everest. Without it, accountability features (goal tracking, weekly review) can't work.

**Impact:** Core accountability feature doesn't run. Iris can't help users track progress toward north star.

**File:** `context/my-mteverest.md`

**Fix:** Add to onboarding: 'What's your Mount Everest (3-5 year goal)?' Populate this file during iris-setup skill.

**Effort:** MEDIUM

### 15. No daily logs exist — blocks weekly review and constraint finder

**Category:** Data

memory/logs/ is empty. Weekly review and constraint finder skills expect historical logs. Can't function.

**Impact:** Skills that depend on activity history can't run until user accumulates logs.

**File:** `memory/logs/`

**Fix:** Create daily log on first session (install.sh does this). Ensure logs are written after each session.

**Effort:** LOW

### 16. tasks.db and iris_accountability.db are empty — built but never wired

**Category:** Data

Databases exist with schema but no code populates them. Task manager skill and accountability engine have no data.

**Impact:** Task tracking and accountability don't persist. Features don't work.

**File:** `data/tasks.db, data/iris_accountability.db`

**Fix:** Wire skills to write to these databases. Test end-to-end.

**Effort:** HIGH

### 17. Iris Core conversation memory resets on VPS restart — in-memory Python dict, not persisted

**Category:** Data

Free tier (Iris Core) stores conversation in a Python dict. On VPS restart, all memory is lost.

**Impact:** Users lose context between sessions. Free tier feels broken on production.

**File:** `.claude/skills/iris-core/scripts/memory.py`

**Fix:** Persist to SQLite or use Upstash for free tier too (optional connection).

**Effort:** MEDIUM

### 18. Phase transition is abrupt — jumps from 'tell me about you' to 'open the dashboard'

**Category:** Onboarding

Setup feels natural until Phase 3, then suddenly 'open http://localhost:5050'. No bridge. Jarring.

**Impact:** Feels like process fell apart. User confidence drops.

**File:** `CLAUDE.md (Phase 2 → Phase 3 transition)`

**Fix:** Add a transition line: 'I've got what I need. Now I need your permission to access your integrations.' Then explain dashboard.

**Effort:** LOW

### 19. Phase 2 has 11 potential questions — feels like a form, not a conversation

**Category:** Onboarding

iris-setup skill lists 11 questions. Even if asked conversationally, it's a lot.

**Impact:** Users get tired. Drop out. Incomplete context.

**File:** `.claude/skills/iris-setup/SKILL.md (Phase 2)`

**Fix:** Cut to 5-6 core questions. Let user volunteer extra info. Don't interrogate.

**Effort:** LOW

### 20. No recovery from interrupted setup — 'pick up where you left off' missing

**Category:** Onboarding

User starts setup, closes tab, comes back. Have to start over. No checkpoint/resume mechanism.

**Impact:** Friction. User might not come back.

**File:** `All onboarding flows`

**Fix:** Save phase progress to database. On return, ask 'Pick up where we left off?' with summary.

**Effort:** MEDIUM

### 21. Upstash marked optional in YAML, treated as required in docs — conflicting signals

**Category:** Documentation

args/preferences.yaml suggests Upstash is optional. But CLAUDE.md says it's required. Which is it?

**Impact:** Users don't know what's mandatory. Build wrong setup.

**File:** `args/preferences.yaml, CLAUDE.md, SKILL.md`

**Fix:** Decide: Is Upstash required or optional? Document consistently everywhere.

**Effort:** LOW

---

## WHAT'S WORKING WELL

✓ Business context (my-business.md) — detailed, substantive, accurate

✓ Voice profile (my-voice.md) — captures real patterns, useful for content generation

✓ Preferences (args/preferences.yaml) — fully configured, timezone/model routing set

✓ Memory (MEMORY.md) — curated, recent, actionable

✓ Skills structure — 26 skills built with proper frontmatter, discoverable

✓ Dashboard connector UI — clean, intuitive, easy to understand

✓ Telegram integration — foundation solid, just needs whitelist fix

✓ Architecture — well-organized, modular, easy to extend

✓ Documentation — CLAUDE.md is thorough and well-written

✓ Hormozi advisor profile — deep (353K words ingested), useful for content strategy

---

## RECOMMENDED FIX ORDER

### Phase 1: Critical (Next 2-3 days)

**3. Auto-populate Telegram whitelist during onboarding** — MEDIUM

**2. Quote .env values to prevent corruption** — LOW

**5. Make Telegram test actually test whitelist + message** — MEDIUM

### Phase 2: Blocking (Next 1 week)

**1. Remove ANTHROPIC_API_KEY from required if not using Anthropic** — LOW

**4. Clear .env when user disconnects connector** — LOW

**11. Check init_db() return value, exit on failure** — LOW

**9. Add file locking to .env writes** — MEDIUM

### Phase 3: Stability (Next 1-2 weeks)

**10. Test memory credentials at connection time, not runtime** — MEDIUM

**6. Add greeting loop detection, suggest next action** — LOW

**7. Confirm unusual inputs before logging to memory** — MEDIUM

**8. Add Anthropic connector to dashboard** — LOW

### Phase 4: Features (Before beta launch)

**14. Add Mount Everest definition to onboarding** — MEDIUM

**16. Wire task manager and accountability DB** — HIGH

**17. Persist Iris Core memory to SQLite** — MEDIUM

### Phase 5: Polish (Before SaaS launch)

**12. Upgrade password hashing to bcrypt/argon2** — MEDIUM

**13. Auto-resync connector registry on file changes** — LOW

**18. Add transition bridge between setup phases** — LOW

**19. Reduce onboarding questions from 11 to 5-6** — LOW

**20. Add setup recovery/checkpoint mechanism** — MEDIUM

**21. Clarify Upstash requirement across all docs** — LOW

