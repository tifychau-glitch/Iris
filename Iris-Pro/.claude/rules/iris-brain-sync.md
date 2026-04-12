# IRIS Brain Sync Protocol

When the user asks to "update the IRIS brain" or "sync iris-brain", this is the signal to:

1. **Refresh BUILD-LOG.md** — Review recent work and ensure all meaningful actions/questions are captured
2. **Refresh TRACKER.md** — Ensure "In Progress", "Recently Completed", and "Known Bugs" are current
3. **Run generate_brain.py** — Compiles the latest state into `output/IRIS-BRAIN.md`

This is a single ritual, not three separate tasks. All three happen together.

## Checklist for "Update IRIS Brain"

Before running the script:
- [ ] Check IRIS-BUILD-LOG.md — any big decisions or questions from recent sessions?
- [ ] Check TRACKER.md — anything move from In Progress → Completed? Any new bugs or ideas?
- [ ] Update dates at the top of both files if any entries were added/changed

Then:
```bash
cd /Users/tiffanychau/Downloads/IRIS/iris-brain/
python3 generate_brain.py
```

The script will:
- Pull the latest TRACKER.md (In Progress, Phase 1 Roadmap, Known Bugs)
- Pull recent BUILD-LOG entries (decisions + questions)
- Pull MEMORY.md, business context, daily logs
- Generate `output/IRIS-BRAIN.md` + copy supporting files

## After generate_brain.py runs:

User will open their Claude.ai Project and:
1. Open the knowledge base
2. Delete old files
3. Drag everything from `output/` into the knowledge base
4. Done — chat Claude now has current context

## When to Trigger This

- Strategy shifts or big decisions made
- User explicitly asks to "update iris-brain" or "sync brain"
- Landing page or voice changed significantly
- Multiple items completed on TRACKER
- Build Log has captured several new actions/questions
- Before a major brainstorm session with chat Claude

Not every session — only when there's meaningful change.
