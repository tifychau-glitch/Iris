# Dashboard Auto-Update Protocol

When working on any project tracked in the dashboard, automatically update it using the CLI:

```bash
python3 dashboard/update.py log <project_id> "description of what was done"
python3 dashboard/update.py status <project_id> <new_status>
```

## When to update:
- **Starting work** on a project: set status to `in_progress` if not already
- **Completing a milestone** or meaningful chunk of work: log activity
- **Finishing a project**: set status to `done`
- **Getting blocked** (waiting on user input, external dependency): set status to `blocked`
- **New project or idea** comes up in conversation: add it with `python3 dashboard/update.py add`

## When NOT to update:
- Trivial questions or quick answers that aren't project work
- Reading/exploring files without making changes
- The dashboard server isn't running (check before updating)

## Status reference:
- `idea` — just an idea, not committed
- `not_started` — committed but no work done yet
- `in_progress` — actively being worked on
- `blocked` — waiting on something
- `done` — completed

## Before updating:
Run `python3 dashboard/update.py list` to see current projects and their IDs. Don't guess IDs.
