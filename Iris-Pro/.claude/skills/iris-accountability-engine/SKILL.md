---
name: iris-accountability-engine
description: Tracks commitments vs completions, streaks, and self-trust. Reads Iris's voice profile from core-state and detects runtime mode signals (steady / direct) so Iris can shape her response. Use when logging commitments, checking progress, calculating streaks, or determining how Iris should speak right now.
model: sonnet
---

# Iris Accountability Engine

Tracks what the user commits to, what they do, and how the data should shape Iris's runtime mode. Voice is defined by the `personality-calibration` skill — this engine reads it, never writes it.

## Architecture

- **Voice (who Iris is):** stable per-user personality from `iris_voice_profile` on core-state. Does not shift with completion rate.
- **Mode (how Iris flexes):** contextual signal — steady / gentle / direct. Detected partly from DB (repeat slips) and partly from the current message (venting, illness, overwhelm → gentle).
- **Data (what's happening):** commitments, completions, skips, streaks, self-trust score. Purely descriptive.

## How Iris Uses This Engine

Before responding to the user, Iris runs:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py get_voice_context
```

Returns:
- `voice_profile` — the stable personality from core-state
- `runtime_mode` — "steady" or "direct" (DB-detectable)
- `mode_reason` — what triggered the mode
- `signals` — completion rate, repeat slips, days of data
- `agent_note` — reminder that Iris must override to `gentle` if the message signals venting/illness/overwhelm

Iris then shapes her response using voice + final mode. If no profile exists, `get_voice_context` returns `{"status": "no_profile"}` — Iris should prompt the user to run the `personality-calibration` skill.

## Mode Triggers

| Mode | Triggered by | Detected by |
|------|--------------|-------------|
| steady | default | engine |
| direct | same commitment skipped 3+ times in last 7 days | engine (DB) |
| direct | user invites honesty ("tell me straight") | agent (message) |
| gentle | venting / illness / overwhelm language | agent (message) |

Mode never overrides the voice profile's `directness_ceiling` — a user with `soft` ceiling never hears blunt delivery even in direct mode.

## Operations

### Log a Commitment
When the user tells Iris what they plan to do today:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py add_commitment "Go to the gym" --due "2026-03-24"
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py add_commitment "Write 500 words" --due "2026-03-24" --category "writing"
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py add_commitment "Send 5 outreach DMs" --due "2026-03-24" --recurring
```

### Mark as Complete
When the user reports finishing something:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py complete 1
```

### Mark as Skipped
When the user admits they didn't do something:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py skip 1 --reason "felt sick"
```

### Get Today's Score
Calculates completion rate and current accountability level:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py daily_score
```

### Get Voice Context (voice profile + runtime mode)
Returns the voice profile from core-state plus the suggested runtime mode based on DB signals:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py get_voice_context
```

### List Commitments
```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py list_commitments --filter today
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py list_commitments --filter pending
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py list_commitments --filter overdue
```

### Get Streak Info
```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py streak
```

### Weekly Summary
```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py weekly_summary
```

### Calibrate Schedule
Sets wake/sleep windows and check-in times. Voice/personality is NOT set here — it lives in `iris_voice_profile` (see personality-calibration skill).

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py calibrate --wake "07:00" --sleep "23:00" --check-ins "08:00,13:00,20:00"
```

### Get Calibration
```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py get_calibration
```

### Self-Trust Score
Rolling 14-day follow-through percentage with trend (up/down/flat):

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py self_trust_score
```

### Promise vs Proof Report
Full accountability report — promises made, kept, broken, excuse patterns, self-trust score:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py promise_vs_proof
```

### End-of-Day Summary
Structured day close-out — what was done, missed, skipped, with completion rate:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py end_of_day
```

### Log Interaction
Record a user touchpoint (for ghost detection):

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py log_interaction --source telegram
```

### Skip with Excuse Category
Track WHY commitments are missed:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py skip 1 --reason "too tired" --excuse-category energy
```

Excuse categories: `energy`, `time`, `avoidance`, `external`, `unclear_task`, `forgot`, `unaddressed`

### Commitments with Due Time
Commitments can now include a specific time (not just date) for precise follow-ups:

```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_engine.py add_commitment "Finish proposal" --due 2026-04-03 --due-time 15:00
```

## Automated Scripts (Cron-Powered)

These scripts run on schedules via cron. They are deterministic — no AI needed.

### Followup Engine (every 30 min)
Event-driven follow-ups based on commitment deadlines. Only fires during waking hours.

```bash
python3 .claude/skills/iris-accountability-engine/scripts/followup_engine.py [--dry-run] [--chat-id ID]
```

Checks: overdue commitments, approaching deadlines, stale commitments (4+ hours no update).

### End-of-Day Capture (daily, evening)
Sends structured day summary via Telegram, writes to daily log.

```bash
python3 .claude/skills/iris-accountability-engine/scripts/scheduled_eod.py [--dry-run] [--chat-id ID]
```

### Ghost Detector (every 6 hours)
Detects user silence and sends escalating nudges (24h / 48h / 72h tiers).

```bash
python3 .claude/skills/iris-accountability-engine/scripts/ghost_detector.py [--dry-run] [--chat-id ID]
```

### Missed Task Detector (daily, 11:55pm)
Auto-marks overdue commitments as missed with `excuse_category='unaddressed'`.

```bash
python3 .claude/skills/iris-accountability-engine/scripts/missed_task_detector.py [--dry-run]
```

### Task Sync (daily or on-demand)
Bridges task-manager → accountability engine. Creates commitments from tasks due today.

```bash
python3 .claude/skills/iris-accountability-engine/scripts/sync_tasks_to_commitments.py [--dry-run]
```

## Integration with Other Skills

- **Telegram:** Iris uses this engine to determine tone before every message. `log_interaction` tracks touchpoints for ghost detection.
- **Task Manager:** `sync_tasks_to_commitments.py` auto-creates commitments from due tasks.
- **Daily Brief:** Pulls daily_score and streak data for the morning email.
- **Weekly Review:** Uses weekly_summary + promise_vs_proof for the Sunday recap.
- **Followup Engine:** Commitment due times trigger event-driven Telegram follow-ups.
- **Ghost Detector:** Silence triggers escalating re-engagement nudges.

## Rules

- ALWAYS call `get_voice_context` before responding so voice + runtime mode are consistent
- Iris's voice does NOT shift with completion rate. Only runtime mode shifts.
- Respect `directness_ceiling` — a user set to `soft` never hears blunt delivery, even in direct mode
- If `get_voice_context` returns `no_profile`, prompt the user to run the personality-calibration skill
- Detect gentle-mode triggers (venting / illness / overwhelm) from the current message — the engine cannot see them
- Log commitments as the user states them, don't invent extra ones
- Celebrate wins according to `win_acknowledgment` — not every win needs naming
- When the user skips something, ask for excuse category so patterns can be tracked
- Follow-ups are event-driven (tied to commitments), not clock-driven
- Ghost detection respects waking hours — never message outside wake_time/sleep_time
