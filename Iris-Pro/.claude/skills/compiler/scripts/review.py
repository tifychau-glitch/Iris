#!/usr/bin/env python3
"""
Review — inspect, approve, reject, and apply compiler proposals.

Usage:
    python3 review.py list                        # list pending proposals
    python3 review.py list --status approved      # filter by status
    python3 review.py show 12                     # show full details of proposal #12
    python3 review.py approve 12                  # mark as approved (not yet applied)
    python3 review.py reject 12                   # mark as rejected
    python3 review.py apply 12                    # write approved proposal to vault
    python3 review.py apply --all-approved        # apply everything currently approved

A proposal must be approved first, then applied. Rejected proposals never
write to the vault. Observations are a review-only type — applying an
observation is a no-op (it's just acknowledged).
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_SCRIPTS = SCRIPT_DIR.parent.parent / "vault" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(VAULT_SCRIPTS))

from compiler_lib import (  # noqa: E402
    list_proposals,
    get_proposal,
    set_status,
)
from vault_lib import write_file, append_to_section, get_vault_path  # noqa: E402


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _type_label(t: str) -> str:
    return {
        "new_concept": "NEW CONCEPT",
        "append_to_effort": "APPEND",
        "observation": "OBSERVATION",
    }.get(t, t.upper())


def _status_label(s: str) -> str:
    return {
        "pending": "pending",
        "approved": "approved (not yet applied)",
        "rejected": "rejected",
        "applied": "applied ✓",
    }.get(s, s)


def format_proposal_short(p: dict) -> str:
    """One-line summary for list view."""
    pid = p["id"]
    ptype = _type_label(p["type"])
    status = _status_label(p["status"])
    title = p.get("title") or p.get("target_file") or (p["content"][:60] + "…")
    return f"  [{pid}] {ptype:12} {status:28} {title}"


def format_proposal_full(p: dict) -> str:
    """Full details for show view."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"Proposal #{p['id']}")
    lines.append("=" * 72)
    lines.append(f"Type:       {_type_label(p['type'])}")
    lines.append(f"Status:     {_status_label(p['status'])}")
    lines.append(f"Run ID:     {p['run_id']}")
    lines.append(f"Created:    {p['created_at']}")
    if p.get("decided_at"):
        lines.append(f"Decided:    {p['decided_at']}")
    if p.get("applied_at"):
        lines.append(f"Applied:    {p['applied_at']}")
    if p.get("title"):
        lines.append(f"Title:      {p['title']}")
    if p.get("target_file"):
        lines.append(f"Target:     {p['target_file']}")
    if p.get("section"):
        lines.append(f"Section:    {p['section']}")
    if p.get("reasoning"):
        lines.append("")
        lines.append("Reasoning:")
        lines.append(f"  {p['reasoning']}")
    if p.get("source_entries"):
        lines.append("")
        lines.append("Sources:")
        for s in p["source_entries"]:
            lines.append(f"  - {s}")
    lines.append("")
    lines.append("Content:")
    lines.append("-" * 72)
    lines.append(p["content"])
    lines.append("-" * 72)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def cmd_list(args):
    status = args.status or "pending"
    proposals = list_proposals(status=status, limit=args.limit)

    if args.format == "json":
        print(json.dumps(proposals, indent=2))
        return 0

    if not proposals:
        print(f"No proposals with status '{status}'.")
        return 0

    print(f"Proposals with status '{status}' ({len(proposals)} shown):")
    print()
    for p in proposals:
        print(format_proposal_short(p))
    print()
    print("Run: review.py show <id>  to see full details")
    print("     review.py approve <id> / reject <id>")
    print("     review.py apply <id>  (after approval)")
    return 0


def cmd_show(args):
    p = get_proposal(args.id)
    if not p:
        print(f"No proposal with id {args.id}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(p, indent=2))
    else:
        print(format_proposal_full(p))
    return 0


def cmd_approve(args):
    p = get_proposal(args.id)
    if not p:
        print(f"No proposal with id {args.id}", file=sys.stderr)
        return 1
    if p["status"] not in ("pending",):
        print(f"Cannot approve proposal in status '{p['status']}' (must be pending)", file=sys.stderr)
        return 1
    if set_status(args.id, "approved"):
        print(f"Proposal #{args.id} approved. Apply with: review.py apply {args.id}")
        return 0
    return 1


def cmd_reject(args):
    p = get_proposal(args.id)
    if not p:
        print(f"No proposal with id {args.id}", file=sys.stderr)
        return 1
    if p["status"] not in ("pending", "approved"):
        print(f"Cannot reject proposal in status '{p['status']}'", file=sys.stderr)
        return 1
    if set_status(args.id, "rejected"):
        print(f"Proposal #{args.id} rejected.")
        return 0
    return 1


def _apply_one(p: dict) -> tuple[bool, str]:
    """Write a single approved proposal to the vault.

    Returns (ok, message).
    """
    if p["status"] != "approved":
        return False, f"proposal #{p['id']} not approved (status: {p['status']})"

    ptype = p["type"]

    if ptype == "observation":
        # Observations are review-only — mark applied without writing
        return True, f"#{p['id']}: observation acknowledged (no file written)"

    if ptype == "new_concept":
        target = p.get("target_file")
        if not target:
            return False, f"#{p['id']}: new_concept missing target_file"
        if not target.startswith("Concepts/"):
            return False, f"#{p['id']}: new_concept must target Concepts/ (got {target})"
        ok, err = write_file(target, p["content"], overwrite=False)
        if not ok:
            return False, f"#{p['id']}: {err}"
        return True, f"#{p['id']}: created {target}"

    if ptype == "append_to_effort":
        target = p.get("target_file")
        section = p.get("section")
        if not target:
            return False, f"#{p['id']}: append_to_effort missing target_file"
        if not section:
            return False, f"#{p['id']}: append_to_effort missing section"
        if not target.startswith("Efforts/"):
            return False, f"#{p['id']}: append_to_effort must target Efforts/ (got {target})"
        ok, err = append_to_section(target, section, p["content"])
        if not ok:
            return False, f"#{p['id']}: {err}"
        return True, f"#{p['id']}: appended to {target} under '{section}'"

    return False, f"#{p['id']}: unknown type {ptype}"


def cmd_apply(args):
    vault = get_vault_path()
    if vault is None:
        print("IRIS_VAULT_PATH is not set — connect a vault first.", file=sys.stderr)
        return 1

    # Collect targets
    if args.all_approved:
        targets = list_proposals(status="approved", limit=500)
        if not targets:
            print("No approved proposals to apply.")
            return 0
    else:
        if args.id is None:
            print("Provide --id or --all-approved", file=sys.stderr)
            return 1
        p = get_proposal(args.id)
        if not p:
            print(f"No proposal with id {args.id}", file=sys.stderr)
            return 1
        targets = [p]

    applied = 0
    failed = 0
    for p in targets:
        ok, msg = _apply_one(p)
        if ok:
            set_status(p["id"], "applied", applied=True)
            applied += 1
            print(f"  ✓ {msg}")
        else:
            failed += 1
            print(f"  ✗ {msg}", file=sys.stderr)

    print()
    print(f"Applied: {applied}, failed: {failed}")
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Review and apply compiler proposals.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List proposals")
    p_list.add_argument("--status", choices=["pending", "approved", "rejected", "applied"])
    p_list.add_argument("--limit", type=int, default=50)

    p_show = sub.add_parser("show", help="Show full details of a proposal")
    p_show.add_argument("id", type=int)

    p_approve = sub.add_parser("approve", help="Approve a proposal (not yet applied)")
    p_approve.add_argument("id", type=int)

    p_reject = sub.add_parser("reject", help="Reject a proposal")
    p_reject.add_argument("id", type=int)

    p_apply = sub.add_parser("apply", help="Apply an approved proposal to the vault")
    g = p_apply.add_mutually_exclusive_group(required=False)
    g.add_argument("id", type=int, nargs="?", default=None)
    g.add_argument("--all-approved", action="store_true")

    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "show": cmd_show,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "apply": cmd_apply,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
