---
name: session-wrap
description: >
  End a session cleanly — auto-journal what happened, update project status, sync memory, and
  compare what was planned vs what got done. Use when user says "/end", "/wrap", "wrap up",
  "end session", "that's it for today", "save everything", or signals they're done working.
user-invocable: true
---

# Session Wrap (/end)

Close out a session by capturing everything that happened, updating project tracking, and surfacing the gap between intention and execution.

## Process

### Step 1: Gather Session Activity

Review the current conversation and collect:
- What tasks were discussed
- What was actually completed (files created, scripts run, decisions made)
- What was planned but NOT completed
- Any commitments made for later ("I'll do X tomorrow", "next week I need to Y")
- Key decisions or insights

### Step 2: Update Daily Log

Append to today's log at `memory/logs/YYYY-MM-DD.md`:

```markdown
## Session: [HH:MM] - [HH:MM]

### Completed
- [What actually got done — be specific]

### Discussed / Planned
- [Topics covered that didn't result in action yet]

### Commitments Made
- [Things the user said they'd do — with deadlines if mentioned]

### Key Decisions
- [Any decisions made during the session]

### Notes
- [Anything else worth remembering]
```

If today's log doesn't exist, create it first:
```markdown
# Daily Log: YYYY-MM-DD

> Session log for [Day, Month DD, YYYY]

---
```

### Step 3: Update Dashboard Projects

Check if any active projects were worked on:

```bash
python3 dashboard/update.py list
```

For each project that had activity:
```bash
python3 dashboard/update.py log PROJECT_ID "description of what was done"
```

If a project status changed (started, completed, blocked):
```bash
python3 dashboard/update.py status PROJECT_ID NEW_STATUS
```

### Step 4: Capture New Commitments

If the user made commitments during the session, log them to the accountability engine:

Check if the accountability engine is available:
```bash
python3 .claude/skills/iris-accountability-engine/scripts/accountability_db.py list_active 2>/dev/null
```

If available, add any new commitments mentioned during the session.

### Step 5: The Gap Report

This is the IRIS touch. Compare:
- What the user said they wanted to do at the start (or what was on their plate)
- What actually got done

**If everything got done:** Brief acknowledgment. No fanfare. "Done. All three shipped."

**If there's a gap:** Name it without judgment.
"You came in wanting to finish the proposal and fix the landing page. Proposal's done. Landing page didn't happen. That's just data — want to slot it for tomorrow?"

**If new things got added but originals didn't move:** Surface the pattern.
"You started with two things. Ended with four new things but the original two are still sitting there. Shiny object energy?"

### Step 6: Close

Keep it short. Forward motion.

"Logged. See you [tomorrow / next time]."

Or if there are pending commitments:
"Logged. You've got [X] on the board for [tomorrow/this week]. I'll check in."

## Voice Rules

- Short. This isn't a performance review — it's a quick save.
- Don't list every single thing that happened. Hit the highlights.
- The gap report is the valuable part. Don't skip it.
- If the session was just a quick question, keep the wrap proportional: "Quick one. Logged."
- Don't be overly positive about completion. Don't be harsh about gaps. Just factual.

## What NOT to Do

- Don't ask for permission to save — just save. That's the point of /end.
- Don't create a new project in the dashboard unless something genuinely new started.
- Don't update MEMORY.md with session-specific details — that's what daily logs are for.
- Don't make this longer than it needs to be. Most wraps should be 3-5 lines to the user.
