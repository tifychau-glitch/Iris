---
name: honest-recommit
description: Silently tracks commitments the user makes with a near-term target date, and counts how many times each one slips (gets postponed, pushed, or missed). After 3 slips, asks ONCE softly whether the commitment is still alive — never nags, never lists. Use this skill whenever the user commits to doing a specific thing by a specific time, or mentions that something they committed to has slipped.
model: haiku
---

# Honest Re-Commitment

Tracks the gap between intention and movement. Different from goal-decay-tracker: that one tracks *attention* (whether a goal has been mentioned), this one tracks *slippage* (whether a commitment keeps getting moved). A thing can slip without going quiet — and a thing can go quiet without ever having slipped.

## Why This Exists

Sometimes the most accountable thing IRIS can do is *ask whether something is still a yes*. Not nag. Not remind. Just give the user permission to drop it consciously. A commitment that keeps getting moved is usually one of two things: either the person is fighting against something real (and needs help seeing it), or the commitment is no longer aligned (and needs to be let go). Either way, the honest question moves things forward.

## Core Principles

1. **Silent capture.** Log commitments and slips without announcing them.
2. **3 slips, then one question.** After the third slip, surface ONCE in the next natural conversation opening. Then drop it.
3. **Soft framing, never failure.** The question is "is this still a yes?" — not "why haven't you done this?"
4. **Permission to let go is the point.** Dropping a commitment consciously is a valid — and often healthy — outcome. The feature is not designed to push users back on track.
5. **One per conversation, max.** Never surface multiple slipped commitments in one message.
6. **Consent-scoped.** Only tracks commitments the user explicitly makes in conversation. Never pulls from calendar or task lists.

## When To Capture a Commitment

Trigger capture when the user says something like:
- "I'll send it by Friday"
- "I'm going to finish the deck tonight"
- "I'll have the proposal done by end of week"
- "I want to ship the landing page this weekend"

Characteristics of a commitment:
- Specific action
- Specific (near-term) time reference
- Stated as an intention, not a wish

**Not a commitment:**
- "I might get to it this week"
- "I'd love to launch the podcast someday" (that's a goal — use goal-decay-tracker)
- Same-day micro tasks ("let me reply real quick")

## When To Record a Slip

A slip happens when:
1. The user mentions that something they committed to didn't happen ("I didn't finish the deck yesterday")
2. The user moves the date on an existing commitment ("I'll get the proposal done by Tuesday instead")
3. The target date passes with no completion reported

Each slip increments the counter. The counter resets only when the commitment is completed or re-committed after IRIS asks.

## Operations

### Capture a commitment

Before capturing, check for an existing match:

```bash
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py find --query "deck"
```

If none exists:

```bash
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py capture \
  --title "finish the deck" \
  --original-text "I'm going to finish the deck tonight" \
  --target-date 2026-04-10
```

### Record a slip

```bash
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py slip \
  --id 3 \
  --new-target-date 2026-04-12 \
  --reason "ran out of time"
```

The response tells you whether a re-commit question should now be surfaced:

```json
{
  "slipped": true,
  "id": 3,
  "slip_count": 3,
  "should_surface": true,
  "commitment": { ... }
}
```

### Mark complete

```bash
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py complete --id 3
```

### Record user's answer to the re-commit question

After IRIS has asked "is this still a yes?", record what the user said:

```bash
# still alive — resets slip counter, sets new target
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py recommit --id 3 --new-target-date 2026-04-15

# let it go
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py archive --id 3 --reason "user let it go"
```

### List active commitments (user-initiated only)

```bash
python3 .claude/skills/honest-recommit/scripts/honest_recommit.py list --status active
```

## How To Surface

When `should_surface` is true, weave one natural question into the conversation:

- "The deck has moved a few times now. Still a yes, or has it passed?"
- "This proposal keeps finding its way off the calendar. Still want to do it?"
- "Heads up — the landing page has slipped a few times. Still alive?"

ONE question. No list. No "you've missed this X times." No guilt. Just the honest question.

The user's answer determines what happens next:
- **"Yes, still doing it"** → call `recommit` with a new target date
- **"No, let it go"** → call `archive`
- **"It changed into X"** → `archive` old, `capture` new

### Re-surfacing rules

After a commitment is re-committed, its slip counter resets to zero. If it slips 3 more times, the question can be asked again — but this is the second time, and IRIS should acknowledge that:

> "This came up a few weeks ago too. Still holding on, or is it time?"

After **2 re-commit cycles** (i.e., asked twice and still slipping), the commitment enters `stopped_asking` state. IRIS will no longer surface on her own — she'll still track it, but the user has to bring it up themselves. This prevents the tool from becoming a nag.

## What Not To Do

- Do not announce captures or slips to the user
- Do not surface more than ONE slipped commitment per conversation
- Do not frame the question as "why haven't you done this?" — always "is this still a yes?"
- Do not ask the question during emotional or vulnerable moments. Read the room.
- Do not mix this with goal-decay-tracker. Goals and commitments are different signals. A commitment can also be a goal, but they're tracked separately.
- Do not pull from calendar/email to detect slips. Only count what the user tells you directly.

## Integration Notes

- Database: `data/commitments.db` (auto-created)
- Feeds into the IRIS Journal automatically
- Runs on Haiku
