# Architecture Visualization Auto-Update Protocol

When making meaningful changes to the IRIS system, update the visual architecture files to keep them accurate.

## Files to update:
- `iris-architecture.html` — Component inventory with build status indicators
- `iris-system-map.html` — Infrastructure topology and data flows

## When to update:
- New skill added or removed
- New MCP connector added or disconnected
- New database or data store created
- Dashboard settings or connectors changed
- New external service integrated
- Build status changes (gray → yellow → green)
- New automation or hook added
- Architecture changes (new agents, new zones, new flows)

## When NOT to update:
- Routine bug fixes within existing code
- Content changes within existing skills (updated prompts, tweaked scripts)
- Config tweaks (.env values, preferences.yaml changes)
- Read-only exploration or research sessions
- Daily log or memory updates

## Current accurate counts (verify before updating):
- Skills: 25
- MCP Connectors: 7 (Gmail, GCal, Slack, Canva, Chrome, Preview, Scheduled Tasks)
- Memory Tiers: 3
- Subagents: 3
- SQLite DBs: 3 (projects.db, tasks.db, iris_accountability.db)
- Deploy Targets: 2 (Local Mac, Hostinger VPS)

## Status dot reference:
- **Green** (Built & Working) — Fully operational, no action needed
- **Yellow** (Built, Needs Config) — Code exists but requires API keys or setup
- **Gray** (Optional / Not Connected) — Available but not wired up

## How to update:
- Match existing HTML patterns and class names (`.card`, `.items`, `.ext-item`, `.props`, etc.)
- Update stat bar numbers in `iris-architecture.html` when counts change
- Update comparison tables in `iris-system-map.html` when capabilities change
- Update the "Current accurate counts" section above after each visual update
