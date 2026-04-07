---
name: advisor-council
description: >
  Create expert advisors from source material and consult them on business decisions.
  Use when user says "create an advisor", "what would [person] say", "ask [person]",
  "run this through the council", "council this", "I want multiple perspectives",
  "add [person] to my advisors", "feed this to [advisor]", or "who are my advisors".
  Also trigger when IRIS recognizes a problem that matches a loaded advisor's expertise.
user-invocable: true
---

# Advisor & Council

Create expert advisors from source material. Consult them individually or run a council for multi-perspective debate. IRIS always mediates and adds her own take.

## Operations

### 1. Create Advisor (`/advisor create`)

Build a new advisor from source material.

**Step 1: Gather Info**

Ask:
- Who is this person? (name, what they're known for)
- What do you want them for? (offers, marketing, operations, mindset, etc.)
- Source material — one or more of:
  - YouTube URL(s) — download transcripts automatically
  - Pasted text, course notes, book highlights
  - File paths to existing documents on disk

**Step 2: Download Sources**

For YouTube URLs, download transcripts:

```bash
python3 .claude/skills/advisor-council/scripts/download_transcript.py "YOUTUBE_URL" "ADVISOR_NAME"
```

This saves the transcript to `context/advisors/{name}/sources/`.

For pasted text or files, save directly to `context/advisors/{name}/sources/` with descriptive filenames.

**Step 3: Synthesize Profile**

Read ALL source material in `context/advisors/{name}/sources/`. Then write `context/advisors/{name}/profile.md` with this structure:

```markdown
# [Name] — Advisor Profile

> One-line summary of who they are and what they're best at.

## Core Frameworks & Mental Models
- [Framework 1]: [How they think about X]
- [Framework 2]: [Their approach to Y]
(Extract the actual named frameworks, processes, and mental models they use)

## Decision-Making Patterns
- What they optimize for (money, time, leverage, freedom, etc.)
- What they'd push back on (common mistakes they call out)
- What they'd encourage (actions they consistently recommend)
- How they prioritize (what comes first in their framework)

## Key Beliefs & Principles
- [Belief 1] — with specific quote or example if available
- [Belief 2]
(The things they repeat across multiple sources — their conviction set)

## Tactical Playbooks
- [Playbook 1]: Step-by-step process they teach for [outcome]
- [Playbook 2]: Their method for [outcome]
(Concrete, actionable processes — not philosophy, execution)

## Communication Style
- How they talk (direct, story-based, data-driven, confrontational, etc.)
- Phrases they use repeatedly
- Their tone when disagreeing or pushing back
- How they'd frame advice (as commands, questions, stories, etc.)

## Blind Spots & Limitations
- What contexts their advice doesn't apply to
- Where their background creates bias
- What they tend to overlook or undervalue

## Expertise Domains
[Comma-separated list of topics this advisor is strong on]
```

**Step 4: Create Source Index**

Write `context/advisors/{name}/source-index.md`:

```markdown
# Source Index: [Name]

| Source | Type | Date Ingested | Key Topics |
|--------|------|---------------|------------|
| [filename] | YouTube/Course/Book/Podcast | YYYY-MM-DD | [topics covered] |
```

**Step 5: Confirm**

Tell the user the advisor is loaded. Mention their strongest domains. Offer to test with a quick question.

### 2. Feed Advisor (Add More Material)

**Trigger:** "Feed [advisor] this" / "Add this to [advisor]"

1. Download or save the new source material to `context/advisors/{name}/sources/`
2. Read the existing `profile.md`
3. Read ALL sources (old + new)
4. Resynthesize — update `profile.md` with new insights, frameworks, or playbooks
5. Update `source-index.md`
6. Confirm what changed: "Added the podcast. He has a new framework on [X] that wasn't in the previous material."

### 3. Consult Advisor (Live, Single)

**Trigger:** "What would [name] say?" / "Ask [name]" / IRIS suggests based on problem domain

**Process:**
1. Read `context/advisors/{name}/profile.md`
2. Read `context/my-business.md` for user context
3. Frame the user's question/problem against the advisor's frameworks
4. Respond with the advisor's perspective in a quoted block
5. Add IRIS's own take — contextualized to what she knows about the user

**Format:**
```
Ran that by [Name].

"[Advisor's response in their voice and framework — 2-5 sentences,
using their communication style and specific terminology]"

[IRIS's take — 1-3 sentences. Agree, disagree, or contextualize.
Reference what she knows about the user's situation, patterns, or history.]
```

**Rules:**
- Advisor speaks in their voice (quoted). IRIS speaks in hers (unquoted).
- IRIS always has the last word.
- If the advisor's frameworks don't clearly apply, say so: "[Name] doesn't really cover this. Want me to try someone else?"
- User can go back and forth — "ask him about the pricing objection" continues the consultation.

### 4. Council (Async, Multi-Advisor)

**Trigger:** "Council this" / "Run this through the council" / "Multiple perspectives"

**Process:**
1. User states the problem or decision
2. Select advisors — user names them, or IRIS picks 3-4 based on the problem domain
3. Read each selected advisor's `profile.md`
4. For each advisor, generate their position:
   - Frame the problem through their specific frameworks
   - Have them argue their position with specifics
   - Note where they'd disagree with common approaches
5. Synthesize:
   - Where do they agree? (brief — agreement isn't the value)
   - Where do they disagree? (this is the value — expand here)
   - What's the strongest argument from each?
6. IRIS delivers the brief and gives her own recommendation

**Format:**
```
Council's back. [N] advisors weighed in.

**[Name 1]** [leans/says] [position]. "[Key quote in their voice — 2-3 sentences]"

**[Name 2]** [leans/says] [position]. "[Key quote in their voice — 2-3 sentences]"

**[Name 3]** [disagrees/splits/agrees]. "[Key quote — 2-3 sentences]"

[If relevant: Where they agreed — 1 sentence]

My take: [IRIS's synthesis — 2-4 sentences. References user's actual situation,
behavioral patterns, or past decisions. Breaks any ties. Pushes toward action.]
```

**Rules:**
- Max 4 advisors per council. More dilutes the signal.
- If all advisors agree, keep it short. The value is in tension.
- IRIS's take must reference something specific to the user — not just summarize.
- Log the council output to today's daily log.
- Don't run a council if only 1 advisor is loaded. Suggest creating more.

### 5. List Advisors

**Trigger:** "Who are my advisors?" / "List advisors" / "What advisors do I have?"

```bash
python3 .claude/skills/advisor-council/scripts/list_advisors.py
```

Shows: name, expertise domains, number of sources, last updated.

## Architecture Notes

- Advisor profiles live in `context/advisors/` — NOT in `.claude/skills/`
- Profiles are only loaded when consulted — no base context bloat
- Raw sources stay on disk in `sources/` — only accessed for deep follow-up questions
- One advisor profile = ~2-4K words = fits easily in a response context
- Council uses sequential generation (not actual parallel subagents) to stay within skill constraints
- Source material has no size limit — synthesis is what gets loaded

## When IRIS Should Proactively Suggest Advisors

- User is stuck on a decision that matches a loaded advisor's domain
- User is about to make a choice that an advisor's framework would challenge
- User asks a question that clearly falls in an advisor's expertise
- Don't suggest advisors for every conversation — only when the match is strong
