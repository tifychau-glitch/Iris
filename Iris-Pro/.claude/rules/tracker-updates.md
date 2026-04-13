# Project Tracker Auto-Update Protocol

TRACKER.md is the single source of truth for all IRIS work. Keep it current.

## When to update TRACKER.md:

- **Starting work** on a tracked item → move it to "In Progress" (or add it if new)
- **Completing work** → move item to "Recently Completed" with `(completed YYYY-MM-DD)`, check the box `[x]`
- **Discovering a bug** → add to "Known Bugs" with `(found YYYY-MM-DD)`
- **User mentions an idea** or shows interest in something → add to "Ideas & Considerations" with `(added YYYY-MM-DD)`
- **New roadmap item** agreed on → add to appropriate phase in "Roadmap"
- **Fixing a bug** → move from "Known Bugs" to "Recently Completed"
- Update the `Last updated:` date at the top

## When NOT to update:

- Quick questions, exploration, or reading files without changes
- Conversations that don't produce deliverables
- Trivial config tweaks or typo fixes

## Item format:

```
- [ ] **Title** — description `#tag` (added YYYY-MM-DD)
- [x] **Title** — description `#tag` (completed YYYY-MM-DD)
```

## Keep it clean:

- "Recently Completed" holds the last ~20 items. When it grows beyond 20, archive older items to the daily log.
- Remove duplicates. If something is in "Ideas" and gets committed, move it to "Roadmap" — don't copy.
- Items that are no longer relevant can be removed with a note in the daily log.

## Tags reference:

`#core` `#dashboard` `#telegram` `#memory` `#accountability` `#skills` `#automation` `#business` `#docs` `#cleanup` `#launch` `#integrations` `#security` `#onboarding` `#email` `#growth` `#marketing`
