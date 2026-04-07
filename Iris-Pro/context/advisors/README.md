# Advisors

Expert advisor profiles synthesized from source material. Each advisor is a consultable persona that IRIS can call on for domain-specific guidance.

## Structure

Each advisor has their own directory:

```
advisors/
├── {name}/
│   ├── profile.md          # Synthesized profile (loaded when consulted)
│   ├── source-index.md     # What sources were ingested
│   └── sources/            # Raw transcripts, notes, course material
│       ├── youtube-video.md
│       └── course-notes.md
```

## How It Works

- **profile.md** is the only file loaded into context when an advisor is consulted (~2-4K words)
- **sources/** are raw materials that stay on disk — referenced only for deep follow-up questions
- More source material = better synthesis, but no context bloat

## Commands

- `/advisor create` — Build a new advisor from source material
- "Ask [name] about X" — Single advisor consultation
- `/council` — Run multiple advisors against a problem
- "Who are my advisors?" — List loaded advisors

## Creating Good Advisors

The best advisors come from:
1. **Paid courses** — highest information density per minute
2. **Books/book notes** — structured thinking, complete frameworks
3. **Long-form podcasts** — unfiltered, nuanced, real examples
4. **YouTube channels** — bulk transcript download for comprehensive coverage

One YouTube video = thin advisor. Three books + a course + 20 podcast appearances = an advisor that actually sounds like the person.
