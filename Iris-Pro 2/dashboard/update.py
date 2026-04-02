#!/usr/bin/env python3
"""CLI to update the project dashboard from Claude or terminal.

Usage:
  python3 dashboard/update.py add "Project Name" --desc "Description" --status idea
  python3 dashboard/update.py status 1 in_progress
  python3 dashboard/update.py log 1 "Built the landing page"
  python3 dashboard/update.py list
  python3 dashboard/update.py task 1 "Complete the landing page"
  python3 dashboard/update.py done <task_id>
  python3 dashboard/update.py tasks 1
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from db import init_db, get_db, add_project, update_status, log_activity, add_task, complete_task

init_db()


def cmd_add(args):
    name = args[0] if args else None
    if not name:
        print("Usage: update.py add \"Project Name\" [--desc \"...\"] [--status idea]")
        return
    desc = ""
    status = "idea"
    i = 1
    while i < len(args):
        if args[i] == "--desc" and i + 1 < len(args):
            desc = args[i + 1]; i += 2
        elif args[i] == "--status" and i + 1 < len(args):
            status = args[i + 1]; i += 2
        else:
            i += 1
    pid = add_project(name, desc, status)
    print(f"Created project #{pid}: {name} [{status}]")


def cmd_status(args):
    if len(args) < 2:
        print("Usage: update.py status <project_id> <new_status>")
        return
    update_status(int(args[0]), args[1])
    print(f"Project #{args[0]} -> {args[1]}")


def cmd_log(args):
    if len(args) < 2:
        print("Usage: update.py log <project_id> \"message\"")
        return
    log_activity(int(args[0]), " ".join(args[1:]))
    print(f"Logged activity for project #{args[0]}")


def cmd_task(args):
    if len(args) < 2:
        print("Usage: update.py task <project_id> \"Task title\"")
        return
    project_id = int(args[0])
    title = " ".join(args[1:])
    tid = add_task(project_id, title)
    print(f"Added task #{tid} to project #{project_id}: {title}")


def cmd_done(args):
    if len(args) < 1:
        print("Usage: update.py done <task_id>")
        return
    complete_task(int(args[0]))
    print(f"Toggled task #{args[0]}")


def cmd_tasks(args):
    if len(args) < 1:
        print("Usage: update.py tasks <project_id>")
        return
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, done FROM tasks WHERE project_id = ? ORDER BY done ASC, created_at ASC",
        (int(args[0]),),
    ).fetchall()
    conn.close()
    if not rows:
        print("No tasks for this project.")
        return
    for r in rows:
        check = "x" if r["done"] else " "
        print(f"  [{check}] #{r['id']}  {r['title']}")


def cmd_list(_):
    conn = get_db()
    rows = conn.execute("SELECT id, name, status, updated_at FROM projects WHERE status != 'archived' ORDER BY updated_at DESC").fetchall()
    conn.close()
    if not rows:
        print("No projects yet.")
        return
    for r in rows:
        print(f"  #{r['id']}  [{r['status']:12s}]  {r['name']}  (updated {r['updated_at'][:16]})")


if __name__ == "__main__":
    commands = {"add": cmd_add, "status": cmd_status, "log": cmd_log, "list": cmd_list, "task": cmd_task, "done": cmd_done, "tasks": cmd_tasks}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Commands: add, status, log, list")
        print("Run with --help or see docstring for usage.")
        sys.exit(1)
    commands[sys.argv[1]](sys.argv[2:])
