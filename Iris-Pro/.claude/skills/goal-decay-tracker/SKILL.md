---
name: goal-decay-tracker
description: Silently captures goals the user shares (things they want to do or build that aren't same-day tasks) and tracks when they last mentioned each one. Surfaces at most ONE stale goal per conversation when a goal has gone quiet long enough, framed softly. Use this skill whenever the user mentions a goal, aspiration, or longer-term thing they want to do.
model: haiku
---

# Goal Decay Tracker

Silent observation layer for goals. Tracks what the user says they want, notices when a goal goes quiet, and surfaces it one at a time — softly.

## Core Principles

1. **Capture is silent.** Never announce that a goal was logged. No "Got it, I'll track that."
2. **Attention, not progress.** The goal's `last_touched` timestamp resets whenever the user mentions it again in any way — win, struggle, plan, or complaint. This isn't a progress tracker; it's an attention tracker.
3. **One stale goal per conversation, max.** Never enumerate multiple stale goals. Never deliver a list.
4. **Soft framing.** When surfacing, ask whether it's still alive — never imply failure. "Still holding onto this, or did it pass?"
5. **Permission to let go is itself accountability.** If the user says "let it go," archive it without judgment. Letting things die consciously is healthy.
6. **Consent-scoped.** Only tracks goals the user explicitly shares. Never infers goals from calendar, email, or other connected tools.

## When to Capture

**Trigger capture** when the user mentions something that:
- Is something they want to do, build, launch, become, or change
- Has a horizon beyond today (not "I need to send this email")
- Is phrased as an aspiration, plan, or direction

Examples of goal-shaped statements:
- "I want to launch the podcast by summer"
- "I'm trying to get the landing page done"
- "I want to start working out again"
- "I'd love to write a book eventually"
- "I need to figure out my pricing model"
- "I'm working toward replacing my salary"

**Do NOT capture:**
- Same-day tasks ("I need to send that email today")
- Things the user is venting about but not committing to
- Hypotheticals ("maybe someday I'd want to...")
- Goals that already exist in the database (instead, update `last_touched`)

## Timeframe Classification

At capture, classify the goal into one of three timeframes. This controls the decay window:

| Timeframe | Decay Window | Signals |
|---|---|---|
| `short` | 7 days | "this week", "in the next few days", explicit dates within ~2 weeks |
| `medium` | 21 days | "this month", "in the next few weeks", no explicit date but language suggests weeks-to-months |
| `long` | 45 days | "this year", "eventually", "someday", major life/business goals |

When unclear, default to `medium`.

## Operations

### Capture a goal

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py capture \
  --title "launch the podcast" \
  --original-text "I want to launch the podcast by summer" \
  --timeframe medium
```

**Important:** Before capturing, check if a similar goal already exists:

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py find --query "podcast"
```

If a match exists, update its `last_touched` instead of creating a duplicate:

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py touch --id 3
```

### Touch a goal (reset decay)

Any time the user mentions an existing goal — even obliquely — touch it:

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py touch --id 3
```

### Check for stale goals

At the start of any conversation, check silently:

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py check_stale
```

Returns at most ONE stale goal — the one that's been quiet longest AND hasn't been surfaced in this session. If nothing is stale, returns empty. If one is returned, weave it softly into the conversation.

**How to surface:**

- "The podcast thing has been quiet for a bit. Still alive, or did it pass?"
- "Haven't heard you mention the landing page lately. Where does it sit right now?"
- "Pricing model came up a few weeks ago and then went quiet. Still on your mind?"

ONE goal. ONE soft question. Then drop it. The user's answer determines what happens next:

- **Still alive** → `touch` the goal (resets decay)
- **Let it go** → `archive` the goal
- **Evolved into something else** → `archive` the old + `capture` the new

### Archive a goal

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py archive --id 3 --reason "user let it go"
```

### List goals (user-initiated only)

Only when the user explicitly asks ("what goals am I tracking?"):

```bash
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py list --status active
python3 .claude/skills/goal-decay-tracker/scripts/goal_decay.py list --status archived
```

Never run this proactively.

### Re-surfacing rules

If a goal was surfaced, the user said "still alive," and then it goes quiet again for another full decay period, it can be surfaced a second time — slightly more pointed:

> "Podcast came up a few weeks ago and you said it was still alive. Been quiet since. Still?"

After **3 re-stales** without any genuine touches, the script stops auto-surfacing that goal. It stays in the database but IRIS doesn't bring it up on her own. The user can always pull it back manually.

### Session-scoped surfacing

The script tracks which goals have been surfaced in the current session (via a session file). This prevents bringing up the same goal twice in one conversation. Session state clears after 6 hours of inactivity.

## What Not To Do

- Do not announce captures to the user
- Do not surface more than ONE stale goal per conversation
- Do not enumerate goals in a list unless explicitly asked
- Do not assume a stated goal means the user is committed — capture anyway, let the decay check sort it out
- Do not judge letting goals go. Archiving is a valid outcome.
- Do not surface stale goals during emotional or vulnerable moments. Read the room.
- Do not pull from calendar, email, or any connected tool. Only capture from conversation.

## Integration Notes

- Database: `data/goals.db` (auto-created)
- Does not depend on any other skill
- Runs on Haiku (classification + date math, no deep reasoning)
- Writes feed into the IRIS Journal automatically via the `iris-journal` skill reading from `goals.db`
