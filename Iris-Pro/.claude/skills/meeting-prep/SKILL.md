---
name: meeting-prep
description: Prepare for meetings with research briefs, talking points, and follow-up templates. Use when user says "prep for meeting with X", "I have a call with X tomorrow", or "meeting brief for X".
model: sonnet
user-invocable: true
---

# Meeting Prep

Create a one-page meeting brief with research, talking points, and follow-up actions.

## Process

### Pre-Meeting Mode (default)

1. **Get context** — Who is the meeting with? What's the context? (sales call, partnership, client check-in, investor meeting)

2. **Research the person/company** — Use the research skill internally:
   - WebSearch for name + company
   - Recent news, content they've published, LinkedIn activity
   - Company: what they do, size, recent changes, challenges

3. **Read business context** — `context/my-business.md` for relevant services to mention

4. **Generate 1-page brief:**

```markdown
## Meeting Brief: [Person Name] — [Company]
**Date:** [date]  |  **Type:** [sales/partnership/client/etc.]

### Who They Are
- [Role, company, background]
- [Recent activity/news]

### What They Likely Need
- [Based on their role + company + industry]
- [Pain points relevant to your services]

### What to Pitch / Discuss
- [Your relevant services from my-business.md]
- [Specific angle based on their situation]

### Questions to Ask
1. [Thoughtful question based on research]
2. [Question about their current challenges]
3. [Question that positions your expertise]

### Potential Objections
- [Likely objection] → [Response]
- [Likely objection] → [Response]

### Prep Notes
- [Anything else relevant — mutual connections, shared interests]
```

5. **Save brief** — Write to `.tmp/meeting-prep/[name]-[date].md`

### Post-Meeting Mode

If user says "meeting notes for [person]" or "I just had a call with [person]":

1. Capture key points from the conversation
2. Extract action items (with owners and deadlines)
3. Draft follow-up email using content-writer voice
4. Update `memory/MEMORY.md` with key relationship facts
5. Create tasks via task-manager skill (if action items exist)

## Rules

- Always check `context/my-business.md` for relevant services
- Research must include recent activity (last 3-6 months if available)
- Brief should be concise — 1 page, scannable in 2 minutes
- Save all briefs to `.tmp/meeting-prep/` for reference
