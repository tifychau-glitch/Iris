---
name: weekly-review
description: Structured weekly business review and planning session. Use when user says "weekly review", "let's do a review", "what happened this week", or at the start of a new week.
user-invocable: true
---

# Weekly Review

Structured review of the past week and planning for the next.

## Process

### Step 1: Gather Data

Read the past 7 days of daily logs from `memory/logs/`:
- Today's log and the 6 preceding days
- If logs don't exist for some days, note which days are missing

Read `memory/MEMORY.md` for current goals and priorities.

Optionally run `scripts/weekly_metrics.py` to parse log files for patterns.

### Step 2: Review Format

Present the review in this structure:

```markdown
## Weekly Review: [Week of Mon DD - Sun DD]

### What Happened This Week
- [Key events, meetings, decisions from logs]
- [Notable accomplishments]
- [Unexpected issues or changes]

### What Got Done
- [Completed tasks and deliverables]
- [Progress on goals from MEMORY.md]

### What Didn't Get Done
- [Tasks that slipped]
- [Why they slipped (if apparent from logs)]

### Patterns & Insights
- [Recurring themes across the week]
- [Time spent on different categories]
- [Energy observations — what drained, what energized]

### Next Week's Plan
- **Priority 1:** [Most important thing]
- **Priority 2:** [Second most important]
- **Priority 3:** [Third most important]
- **Carry-over:** [Tasks from this week that roll forward]

### Goals Check
- [Progress against 90-day goals from MEMORY.md]
- [Any goal adjustments needed?]
```

### Step 3: Update Memory

After the review:
1. Update `memory/MEMORY.md` with new priorities if they've changed
2. Create next Monday's daily log template with the priorities
3. Ask user if any goals need adjustment

## Script

`scripts/weekly_metrics.py` — Parses daily logs and extracts:
- Number of events per day
- Common themes/keywords
- Tasks mentioned as completed

## Rules

- Be honest about what didn't get done — don't spin it
- If logs are sparse, note this and suggest better logging habits
- Keep the review concise — scannable in 5 minutes
- The planning section is the most important output — make it actionable
