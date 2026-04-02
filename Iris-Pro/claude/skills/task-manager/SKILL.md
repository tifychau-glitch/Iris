---
name: task-manager
description: Simple task and project tracking with SQLite database. Use when user says "add a task", "what's on my plate", "show my tasks", "mark X as done", "what's due this week", or manages tasks/projects.
user-invocable: true
---

# Task Manager

SQLite-backed task and project tracking.

## Operations

### Add Task
User: "Add a task: follow up with Sarah by Friday"

Parse: title, description (optional), due date (optional), priority (optional), project (optional), tags (optional).

```bash
python3 scripts/task_db.py add --title "Follow up with Sarah" --due "2026-02-28" --priority high
```

### List Tasks
User: "What's on my plate?" / "Show my tasks" / "What's due this week?"

```bash
python3 scripts/task_db.py list                      # All open tasks
python3 scripts/task_db.py list --status pending      # Pending only
python3 scripts/task_db.py list --due-this-week       # Due this week
python3 scripts/task_db.py list --project "client-x"  # By project
python3 scripts/task_db.py list --priority high       # By priority
```

Present as a clean table:
```
| # | Task | Due | Priority | Project |
|---|------|-----|----------|---------|
| 1 | Follow up with Sarah | Feb 28 | High | Sales |
```

### Complete Task
User: "Mark 'follow up with Sarah' as done"

```bash
python3 scripts/task_db.py complete --id 1
```

Log the completion in today's daily log.

### Update Task
User: "Push Sarah follow-up to next Monday" / "Change priority to low"

```bash
python3 scripts/task_db.py update --id 1 --due "2026-03-02"
python3 scripts/task_db.py update --id 1 --priority low
```

### Delete Task
User: "Remove task #3"

```bash
python3 scripts/task_db.py delete --id 3
```

Always confirm before deleting.

## Integration

- **Weekly review** reads incomplete tasks to include in the review
- **Meeting prep** can create follow-up tasks after meetings
- **Daily log** records task completions

## Rules

- Always confirm task details before adding (especially due dates parsed from natural language)
- When listing tasks, sort by: overdue first, then by due date, then by priority
- When a task is completed, note it in today's daily log
- Don't create duplicate tasks — check existing tasks first
