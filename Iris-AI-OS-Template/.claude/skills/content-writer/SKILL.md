---
name: content-writer
description: Create content in the user's voice — LinkedIn posts, emails, blog posts, proposals, or ad copy. Use when user says "write a post about X", "draft an email to X", "create content about X", or "write copy for X".
agent: content-writer
user-invocable: true
---

# Content Writer

Create content that sounds like the user, not like AI.

## Before Writing Anything

**Mandatory reads:**
1. `context/my-voice.md` — How the user communicates
2. `context/my-business.md` — Business context for relevance
3. `args/preferences.yaml` — Platform preference, post length

If `context/my-voice.md` is a placeholder, tell the user to run the business-setup wizard first.

## Process

1. **Understand intent** — What type of content? What's the goal? Who's the audience?
2. **Read context files** — Voice guide and business context (mandatory)
3. **Draft** — Write content matching the user's voice
4. **Voice check** — Review against voice guide. Does this sound like them or like AI?
5. **Refine** — Fix any generic AI patterns (see anti-patterns below)
6. **Present** — Show the content ready to use

## Content Types

### LinkedIn Posts
- Short: ~300 characters (quick thought)
- Medium: ~600 characters (insight + example)
- Long: ~1200 characters (story + lesson + CTA)
- Use line breaks for readability
- Hook in the first line
- End with engagement prompt or CTA

### Emails
- Subject line + body
- Match user's email tone (usually different from social tone)
- Professional but not stiff (unless that's their style)

### Blog Posts
- Structured with headers
- User's voice throughout
- Practical, not theoretical (unless requested)

### Proposals
- Professional, persuasive
- Reference business context for credibility
- Clear pricing/scope sections

## AI Anti-Patterns (Never Use)

- "In today's fast-paced world..."
- "Let's dive in..."
- "Here's the thing..."
- "Game-changer"
- "Leverage", "synergy", "ecosystem" (unless user actually uses these)
- Starting every sentence with "I"
- Generic motivational conclusions
- Overusing em-dashes and semicolons

## Input Sources

Content can be created from:
- A topic ("write about lead generation")
- A transcript ("turn this video into a post")
- Notes ("here are my thoughts, clean them up")
- A brief ("LinkedIn post, targeting CTOs, about AI automation")
- An existing piece ("rewrite this in my voice")

## Rules

- Never write without reading the voice guide first
- Never present first drafts as final — always do the voice check
- If the user doesn't like the output, ask what specifically doesn't sound like them and update the voice guide
