---
name: fact-check
description: Verify factual claims in any AI-generated response or block of text. Use when user says "fact-check this", "is this accurate?", "check for hallucinations", "verify this", or "check the last response".
model: sonnet
context: fork
user-invocable: true
---

# Fact-Check

Verify the factual accuracy of any text — AI responses, best-practices lists, technical claims — by extracting claims, assessing risk, and cross-referencing live sources.

## Process

1. **Accept input** — The user will either:
   - Paste a block of text to verify
   - Say "check the last response" — in which case, use the most recent AI response in the conversation

2. **Extract claims** — Parse the text and list every distinct factual assertion. Skip opinions, instructions, and phrasing like "it depends." Focus on:
   - Named tools, libraries, frameworks, or technologies
   - Version numbers, release dates, or timelines
   - Statistics, percentages, or numeric claims
   - Attributed quotes or statements
   - Claims about how something works technically
   - Best practices labeled as current or standard

3. **Assign risk tier to each claim:**
   - **High-risk** — Recent events, version numbers, specific stats, named tools/libraries, attributed quotes, anything that changes over time. *Search these.*
   - **Low-risk** — Fundamental concepts that have been stable for years (e.g., "SQL is a relational query language"). *Accept without searching.*

4. **Verify high-risk claims** — For each high-risk claim:
   - Run `WebSearch` with a targeted query
   - Read at least 2 results (use `WebFetch` for full content if needed)
   - Determine: Verified / Uncertain / Likely Incorrect

5. **Compile the report** — Use the output format below.

6. **Offer to correct** — If any claims are Uncertain or Incorrect, offer to re-answer the original question with accurate information.

## Output Format

```
## Fact-Check Report

**Source:** [first 100 chars of input text...]
**Checked:** YYYY-MM-DD

---

### ✓ Verified
- **[claim]** — [source URL, 1-line note on what confirmed it]

### ⚠ Uncertain
- **[claim]** — [what was found, why it couldn't be confirmed, or conflicting results]

### ✗ Likely Incorrect
- **[claim]** — [what the evidence actually shows + source URL]

### — Accepted Without Search (Low-Risk)
- [claim]
- [claim]

---

**Summary:** X of Y claims verified. Z flagged.
[One line on overall reliability of the source text.]
```

## Rules

- **Never mark something Verified without a source.** If you can't find confirmation, mark Uncertain.
- **Paywalled or inaccessible results count as Uncertain**, not Verified.
- **Flag when a claim was true but is now outdated** — e.g., a library's API changed, a best practice was superseded.
- **Don't inflate the Incorrect count.** A slightly imprecise claim isn't wrong — mark it Uncertain with a note.
- **Be honest about limits.** Niche topics, internal tooling, or very recent events may have no web evidence. Say so.
- **Low-risk claims don't need searching** — use judgment. Verifying "Python is a programming language" wastes time.
- Save report to `.tmp/fact-check/[date]-[topic-slug].md` when the input is long or the user may want to reference it later.
