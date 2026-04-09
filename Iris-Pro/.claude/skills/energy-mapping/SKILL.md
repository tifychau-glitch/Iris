---
name: energy-mapping
description: Silently logs when the user reports finishing or shipping something, then maps when their actual productive windows are (hour-of-day and day-of-week patterns). Surfaces ONE insight on demand or once enough data accumulates. Use this skill whenever the user mentions completing, shipping, finishing, sending, publishing, or wrapping up something.
model: haiku
---

# Energy Mapping

Tracks when the user *actually* ships things — not when they planned to, not what's on their calendar, just what gets reported done — and maps the real productive windows over time. The point is to surface windows the user can't see themselves: "you do your best work between 9 and 11am, but you schedule meetings then."

## Core Principles

1. **Silent capture.** Log every time the user reports shipping something. Never announce.
2. **Consent-scoped.** Only logs from explicit user statements. Never reads calendar, git, email, or any connected tool to infer activity.
3. **Insight at threshold, not before.** Patterns require data. Don't surface anything until at least 15 events are logged AND a clear pattern exists. Below that, the data is noise.
4. **One insight at a time, on demand.** When the user asks "when do I work best?" — answer. Otherwise, only offer once when the threshold is first crossed, then drop it.
5. **No moral framing.** This is not about "you should work more in the morning." It's data the user can use however they want.

## When To Capture

Trigger capture when the user says variations of:
- "I just finished the newsletter"
- "Shipped the landing page"
- "Sent the proposal"
- "Wrapped up the deck"
- "Done with the email batch"
- "Got the prototype working"

**Do NOT capture:**
- Plans or intentions ("I'm going to finish this")
- Updates mid-task ("still working on the deck")
- Vague status ("had a productive morning")
- Things explicitly already tracked elsewhere as commitments completing — but actually, capture both. The energy map cares about the *when*, not the *what*.

## Optional Categorization

Each event can optionally be tagged with a category — `creative`, `admin`, `meeting`, `outreach`, `coding`, `writing`, etc. This lets the user later ask "when do I do my best creative work?" vs. "when do I ship admin stuff?" Categorization is optional and defaults to `general`.

## Operations

### Log a shipped event (silent)

```bash
python3 .claude/skills/energy-mapping/scripts/energy_mapping.py log \
  --what "newsletter draft" \
  --category writing
```

The timestamp is captured automatically (server time). Returns silently.

```json
{
  "logged": true,
  "id": 17,
  "timestamp": "2026-04-09T10:42:00",
  "category": "writing",
  "total_events": 17,
  "threshold_crossed": false
}
```

### Check if there's a pattern to surface

After every log, check if a fresh insight is available:

```bash
python3 .claude/skills/energy-mapping/scripts/energy_mapping.py check_insight
```

Returns at most ONE insight, or null. Insights only surface when:
- At least 15 events are logged
- A clear hour-of-day or day-of-week pattern exists (≥40% of events in a single time bucket)
- The insight has not yet been surfaced this session AND has not been surfaced in the last 14 days

### Get pattern summary (user-initiated)

When the user asks "when do I actually work best?":

```bash
python3 .claude/skills/energy-mapping/scripts/energy_mapping.py summary
```

Returns a full breakdown:
- Top 3 productive time-of-day windows
- Top 3 productive days of the week
- Per-category breakdowns (if categories were used)
- Total events analyzed and date range

### List recent events

```bash
python3 .claude/skills/energy-mapping/scripts/energy_mapping.py list --days 30
```

User-initiated only.

## How To Surface an Insight

When `check_insight` returns one, weave it naturally into the conversation:

- "I've been quietly tracking when you tell me you've finished things. There's a pattern — most of what you ship lands between 9 and 11am. Useful to know?"
- "Quick observation — Tuesdays seem to be your highest-output day so far. Worth protecting?"
- "Noticed something. Almost everything you've described as 'creative work' has happened in the morning. Afternoons tend to be admin."

ONE insight. ONE optional question. Then drop it. The user's response determines whether to dig deeper.

**Never list multiple insights.** Even if there are three patterns, surface only the strongest one.

## What Not To Do

- Do not surface insights below 15 events. The data isn't meaningful yet.
- Do not surface the same insight twice within 14 days
- Do not infer activity from calendar, git, email, or any external tool
- Do not frame insights as judgments ("you should be working harder mornings")
- Do not rank or score the user's productivity. The map describes; it doesn't grade.

## Integration Notes

- Database: `data/energy_events.db` (auto-created)
- Feeds into the IRIS Journal automatically
- Runs on Haiku
