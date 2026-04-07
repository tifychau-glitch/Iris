# IRIS Brain

Personal tooling to keep Claude.ai (web chat) in sync with the actual state of IRIS.

**This folder is NOT part of the IRIS product.** It lives outside `Iris-Pro/` on purpose so it never ships to customers. Do not move it inside `Iris-Pro/`.

## What It Does

Generates a bundle of files you can drag into a Claude.ai Project so chat Claude has real, current context about IRIS — strategy, status, landing page code, dashboard code, your voice — without you having to re-explain every time.

## Files

- `generate_brain.py` — Reads from `Iris-Pro/` and `iris-landing-page/`, compiles a bundle in `output/`
- `system-prompt.md` — Paste this into your Claude Project's system prompt (one-time setup)
- `wrestling.md` — **You edit this.** Open questions and things you've ruled out. The script pulls from it.
- `output/` — Generated bundle. Drag contents into your Claude Project knowledge base.

## Workflow

**One-time setup:**
1. Create a new Claude Project at claude.ai
2. Open `system-prompt.md`, copy the contents into the Project's system prompt field

**Every time things change:**
1. Tell Claude Code "update the IRIS brain" (or run `python3 generate_brain.py` manually)
2. Open your Claude Project knowledge base
3. Delete the old files
4. Drag everything from `output/` into the knowledge base
5. Done — chat is current

## When to Update

- Strategy shifts
- New decisions made
- Landing page copy changed
- Tracker status changed meaningfully
- You updated `wrestling.md` with new questions

Not every day. When something actually moved.

## What Gets Generated

```
output/
├── IRIS-BRAIN.md           # strategic state, status, decisions
├── landing-page.html       # current landing page source
├── dashboard-index.html    # current dashboard UI
├── dashboard-settings.html # settings page
└── my-voice.md             # voice guide
```

For visual feedback on design, screenshot per-conversation. Chat Claude will already have the underlying code to reference.
