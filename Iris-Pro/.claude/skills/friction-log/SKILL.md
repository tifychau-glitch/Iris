---
name: friction-log
description: Silently captures friction — the reasons things don't happen — when the user mentions blockers in conversation, and surfaces patterns only when the same category shows up 3+ times in 30 days. Use this skill whenever the user says something like "I couldn't because...", "I was going to but...", "I meant to but...", or describes why something they planned didn't happen.
model: haiku
---

# Friction Log

Quiet observation layer for accountability. Captures the *reasons* things don't happen, in the user's own words, and surfaces patterns only once they're real.

## Core Principles

1. **Capture is silent.** Never announce that you logged something. No "I'll make a note of that." No "I noticed..." The user should not feel watched.
2. **Surface at 3+, once.** Only mention a pattern after the same category has appeared 3 or more times in the last 30 days — and only the first time it crosses that threshold. After surfacing, mark it and don't nag.
3. **One thing at a time.** Never list multiple frictions. Never deliver receipts. Surface ONE pattern, woven into natural conversation.
4. **User's words matter.** Store the actual friction text verbatim. The category is a tag, not a replacement for what they said.
5. **Not a judgment engine.** Friction is data, not moral evaluation. A sick kid and avoidance both log the same way. The pattern speaks for itself.

## When To Use

**Trigger capture** when the user says any variation of:
- "I couldn't because..."
- "I was going to but..."
- "I meant to but..."
- "I didn't get to it because..."
- "I would have, but..."
- "I got pulled into..."
- "I ran out of..."
- "I was too [tired/busy/overwhelmed]..."
- Any other phrasing where they explain why something planned didn't happen

**Do NOT trigger capture** for:
- General complaints not tied to a specific thing that didn't happen
- Past tense storytelling about things long resolved
- Hypothetical statements ("if I get busy I might not...")
- Things the user explicitly says don't count ("forget I said that")

## Friction Categories

Classify each friction into ONE of these categories:

| Category | Examples |
|---|---|
| `interruption` | Pulled into a client call, unexpected meeting, kid interrupted |
| `energy` | Too tired, no energy, drained, burned out |
| `focus` | Couldn't focus, scattered, kept getting distracted |
| `time` | Ran out of time, day got away, no time |
| `blocked_external` | Waiting on feedback, someone else didn't deliver, dependency |
| `environment` | Setup not ready, tool broken, wrong location |
| `distraction` | Doom-scrolling, social media, got sidetracked |
| `caregiving` | Kid sick, family needed me, caregiving duties |
| `scope_unclear` | Didn't know where to start, overwhelmed by size |
| `avoidance` | Didn't feel like it, put it off, kept finding other things to do |
| `email_overwhelm` | Spent morning on email, inbox consumed me |
| `shiny_object` | New idea pulled me, chased something else |
| `other` | Doesn't fit any category |

When uncertain, pick the closest match. The category is for pattern detection, not precision.

## Operations

### Log friction (silent capture)

After classifying, log it:

```bash
python3 .claude/skills/friction-log/scripts/friction_log.py log \
  --thing "newsletter" \
  --friction-text "I was going to write the newsletter but I got pulled into a client call" \
  --category interruption
```

The script will:
1. Insert the friction into the database
2. Check if this category now has 3+ occurrences in the last 30 days
3. Return a JSON response with `should_surface: true/false` and pattern details

### Check for pattern (after every log)

The `log` command returns pattern info automatically. Example response:

```json
{
  "logged": true,
  "id": 42,
  "category": "interruption",
  "should_surface": true,
  "pattern": {
    "category": "interruption",
    "count": 4,
    "recent_examples": [
      "pulled into a client call",
      "kid interrupted me mid-sentence",
      "unexpected meeting popped up",
      "client called and it went long"
    ],
    "first_seen": "2026-03-15",
    "latest": "2026-04-08"
  }
}
```

If `should_surface` is `true`, weave a natural observation into your next response. Examples:

- "Client stuff has been pulling you off things a few times lately. Worth a look at how those are landing?"
- "Focus has come up a few times now when things slip. Anything shifting there?"
- "Energy has been the blocker a few times recently. How's that actually been?"

**Rules for surfacing:**
- ONE observation, not a list
- Woven into the conversation, not announced as a report
- Optional follow-up question (one, maximum)
- Never enumerate the individual instances ("on Monday you said X, on Wednesday you said Y...")
- Never frame as failure or receipts
- After surfacing, the script automatically marks the pattern as surfaced — it won't re-surface unless it goes quiet and comes back strong

### List recent friction (on-demand, user-initiated only)

Only when the user explicitly asks ("what have I been hitting lately?"):

```bash
python3 .claude/skills/friction-log/scripts/friction_log.py list --days 30
```

Never run this proactively. This is pull, not push.

### Remove a misclassified friction

If the user corrects you ("that wasn't really friction"):

```bash
python3 .claude/skills/friction-log/scripts/friction_log.py remove --id 42
```

### Get pattern status (debug / introspection)

```bash
python3 .claude/skills/friction-log/scripts/friction_log.py patterns
```

Returns all categories with 3+ occurrences in the last 30 days and their surface status.

## Decay

Friction older than 60 days is excluded from pattern counts. The database keeps the records, but old noise doesn't haunt current observations. A pattern has to be *currently active* to surface.

## What Not To Do

- Do not tell the user you're logging their friction
- Do not surface patterns below 3 occurrences
- Do not re-surface patterns that have already been surfaced (unless they go quiet for 14+ days and come back)
- Do not list multiple patterns in one message
- Do not use the friction log to justify tone escalation — that's what the accountability engine does
- Do not surface friction during emotional or vulnerable moments. Read the room. Patterns can wait.
- Do not correlate friction with specific projects unless the user themselves draws the connection

## Integration Notes

- Database: `data/friction_log.db` (auto-created on first use)
- Does not depend on any other skill
- Does not read from calendar, email, Slack, or any connected tool — captures only from conversation
- Runs on Haiku (simple classification, fast)
