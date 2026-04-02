---
name: research
description: Deep research on any topic — competitors, markets, technologies, people, or companies. Use when user says "research X", "look into X", "what do we know about X", or "competitive analysis on X".
model: sonnet
context: fork
user-invocable: true
---

# Research

Investigate any topic thoroughly and return structured findings.

## Process

1. **Clarify scope** — What specifically does the user want to know? Ask if the request is vague.

2. **Research** — Use available tools in this order of preference:
   - WebSearch (always available, no API key needed)
   - WebFetch (for specific URLs)
   - Perplexity MCP (if configured — deeper synthesis)
   - Firecrawl (only for scraping specific URLs, NOT for research)

3. **Cross-reference** — Check at least 2-3 sources. Flag conflicting information.

4. **Structure findings** — Organize into the output format below.

5. **Save to scratch** — Write the full brief to `.tmp/research/[topic]-[date].md`

## Output Format

```markdown
## Research Brief: [Topic]

### Summary
[2-3 sentence overview of key findings]

### Key Findings
- [Finding 1] — Source: [URL or reference]
- [Finding 2] — Source: [URL or reference]
- [Finding 3] — Source: [URL or reference]

### Details
[Deeper analysis organized by subtopic]

### Open Questions
[Things you couldn't confirm or need more investigation]

### Sources
1. [URL] — [what it contributed]
2. [URL] — [what it contributed]
```

## Research Types

**People:** LinkedIn profile, recent activity, company role, mutual connections, public speaking, content they've published.

**Companies:** What they do, size, funding, tech stack, recent news, competitors, leadership, hiring signals.

**Markets:** Size, growth rate, key players, trends, regulation, opportunities, threats.

**Topics:** Current state of the art, key concepts, recent developments, expert opinions, practical applications.

## Rules

- Always cite sources — never present unsourced claims as fact
- Distinguish between facts, estimates, and opinions
- Flag when information is outdated (older than 6 months for fast-moving topics)
- If you can't find reliable information, say so — don't fill gaps with speculation
- Save all research output to `.tmp/research/` for future reference
