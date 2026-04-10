#!/usr/bin/env python3
"""
Compiler — read the journal + vault, propose vault updates.

Reads:
  - Recent entries from the 4 silent-capture DBs (via iris-journal)
  - Identity files from the user's vault (via vault_lib)

Asks an LLM to propose:
  - New `Concepts/` articles synthesizing patterns IRIS has noticed
  - Observations about gaps between aspiration (vault) and behavior (journal)
  - Appends to existing `Efforts/` files when journal entries match a project

Stores proposals in data/compiler_proposals.db as 'pending'.
User reviews via review.py and approves or rejects each one.
Only on approval does anything land in the vault.

Usage:
    python3 compile.py                          # run, 14 day window
    python3 compile.py --days 30                # custom window
    python3 compile.py --dry-run                # skip LLM call, just show what we'd send
    python3 compile.py --mock-llm               # use a fake LLM response (for testing)
    python3 compile.py --format json            # JSON output
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
VAULT_SCRIPTS = PROJECT_ROOT / ".claude" / "skills" / "vault" / "scripts"
JOURNAL_SCRIPT = PROJECT_ROOT / ".claude" / "skills" / "iris-journal" / "scripts" / "journal.py"

sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(VAULT_SCRIPTS))
sys.path.insert(0, str(PROJECT_ROOT))

from compiler_lib import init_db, add_proposal  # noqa: E402
from vault_lib import get_vault_path, read_file, list_files  # noqa: E402


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------

def load_journal_entries(days: int) -> dict:
    """Run iris-journal and return its JSON output as a dict.

    Returns {"count": 0, "entries": []} if the journal script fails or
    there's no data.
    """
    if not JOURNAL_SCRIPT.exists():
        return {"count": 0, "entries": [], "error": "journal script not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(JOURNAL_SCRIPT), "read",
             "--days", str(days), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"count": 0, "entries": [], "error": "journal read timed out"}
    except Exception as e:
        return {"count": 0, "entries": [], "error": f"journal error: {e}"}

    if result.returncode != 0 or not result.stdout.strip():
        return {"count": 0, "entries": [], "error": f"journal returned no data: {result.stderr[:200]}"}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"count": 0, "entries": [], "error": "journal returned invalid JSON"}


def load_vault_identity() -> dict:
    """Load identity files from the vault. Returns dict with file → content.

    Returns {"available": False} if no vault configured or found.
    """
    vault = get_vault_path()
    if vault is None or not vault.exists():
        return {"available": False, "reason": "vault not configured or missing"}

    files_to_load = [
        "me.md",
        "my-everest.md",
        "my-business.md",
        "my-voice.md",
        "maps/iris-rules.md",
    ]

    identity = {"available": True, "vault_path": str(vault), "files": {}}
    for f in files_to_load:
        content, err = read_file(f)
        identity["files"][f] = content if content is not None else None

    # Also list existing Concepts/ and Efforts/ files so the LLM can avoid duplicates
    concepts, _ = list_files(subfolder="Concepts")
    efforts, _ = list_files(subfolder="Efforts")
    identity["existing_concepts"] = concepts or []
    identity["existing_efforts"] = efforts or []

    return identity


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are IRIS's compiler. Your job is to look at what IRIS has silently observed about the user (the "journal") and their written identity in their Obsidian vault, and propose structured updates that promote raw observations into compiled knowledge.

You propose updates. You do NOT apply them. The user will review and approve each proposal before anything is written.

PRINCIPLES:
1. Quality over quantity. 0-5 strong proposals is better than 10 weak ones. If nothing stands out, return an empty list.
2. Honor the user's voice. If the vault has `my-voice.md`, match that style in any content you propose.
3. Respect the trust contract. Never propose edits to identity files (me.md, my-everest.md, etc.) — only new Concepts/ files, appends to Efforts/, or flagged observations.
4. Be specific. Vague synthesis is worse than no synthesis. Every proposal must cite the journal entries or identity sections that support it.
5. Don't moralize or frame around failure. Observations should be neutral and factual.

PROPOSAL TYPES:
- "new_concept": Create a new file in Concepts/. Use when you notice a pattern across multiple journal entries worth promoting to compiled knowledge. Must include target_file (e.g. "Concepts/shipping-patterns.md"), title, content (full markdown body).
- "append_to_effort": Append a note under a reserved section in an existing Efforts/ file. Use when a journal entry relates to an active project. Must include target_file (must exist), section (e.g. "Iris Notes"), content.
- "observation": A gap between what the vault says and what the journal shows. Surfaced for the user, not applied to any file. Use when the user's behavior contradicts their stated priorities or values. Must include content (the observation itself).

Return a JSON object with this exact shape:
{
  "proposals": [
    {
      "type": "new_concept" | "append_to_effort" | "observation",
      "target_file": "Concepts/<slug>.md" or "Efforts/<existing>.md" or null (for observation),
      "section": "<heading>" or null,
      "title": "<short title>" or null,
      "content": "<full markdown body>",
      "reasoning": "<1-2 sentences explaining why this matters>",
      "source_entries": ["<reference to journal entry ids or file sections>"]
    }
  ]
}

If there is nothing to propose, return {"proposals": []}.

Return ONLY valid JSON, no commentary, no markdown fences."""


def build_user_prompt(journal_data: dict, identity: dict, days: int) -> str:
    """Build the user-side prompt: the journal + identity data the LLM should reason over."""
    lines = []
    lines.append(f"# Data for compiler run")
    lines.append(f"Window: last {days} days")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append("")

    # Vault identity
    lines.append("## Vault Identity Files")
    if not identity.get("available"):
        lines.append(f"_(vault not available: {identity.get('reason', 'unknown')})_")
    else:
        lines.append(f"_Vault path: {identity['vault_path']}_")
        lines.append("")
        for fname, content in identity.get("files", {}).items():
            lines.append(f"### `{fname}`")
            if content is None:
                lines.append("_(file not found)_")
            else:
                lines.append(content.strip())
            lines.append("")

        lines.append(f"### Existing Concepts/ files")
        concepts = identity.get("existing_concepts", [])
        if concepts:
            for c in concepts:
                lines.append(f"- {c}")
        else:
            lines.append("_(none yet)_")
        lines.append("")

        lines.append(f"### Existing Efforts/ files")
        efforts = identity.get("existing_efforts", [])
        if efforts:
            for e in efforts:
                lines.append(f"- {e}")
        else:
            lines.append("_(none yet)_")
        lines.append("")

    # Journal entries
    lines.append("## Journal Entries (what IRIS has silently observed)")
    count = journal_data.get("count", 0)
    lines.append(f"_Total entries in window: {count}_")
    if journal_data.get("error"):
        lines.append(f"_(journal error: {journal_data['error']})_")
    lines.append("")

    entries = journal_data.get("entries", [])
    if not entries:
        lines.append("_(no journal entries yet — the silent-capture skills haven't recorded anything)_")
    else:
        for i, entry in enumerate(entries, 1):
            lines.append(f"### Entry {i}")
            lines.append(f"- **Timestamp:** {entry.get('timestamp', 'unknown')}")
            lines.append(f"- **Source:** {entry.get('source', 'unknown')}")
            lines.append(f"- **Type:** {entry.get('type', 'unknown')}")
            if entry.get("thing"):
                lines.append(f"- **Thing:** {entry['thing']}")
            lines.append(f"- **What:** {entry.get('what', '').strip()}")
            if entry.get("state"):
                lines.append(f"- **State:** {entry['state']}")
            if entry.get("note"):
                lines.append(f"- **Note:** {entry['note']}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Based on the above, propose vault updates following the rules in the system prompt. Return JSON only.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(system_prompt: str, user_prompt: str, tier: str = "default") -> str:
    """Route the request through the ai_provider abstraction."""
    try:
        from lib.ai_provider import ai
    except ImportError as e:
        return json.dumps({
            "proposals": [],
            "error": f"ai_provider not available: {e}",
        })

    try:
        return ai.reason(system_prompt, user_prompt, tier=tier, timeout=180)
    except Exception as e:
        return json.dumps({
            "proposals": [],
            "error": f"LLM call failed: {e}",
        })


def mock_llm_response() -> str:
    """Return a fake LLM response for testing without hitting a real API."""
    return json.dumps({
        "proposals": [
            {
                "type": "new_concept",
                "target_file": "Concepts/mock-pattern.md",
                "section": None,
                "title": "Mock Pattern (Test Data)",
                "content": "# Mock Pattern\n\nThis is a test proposal generated by --mock-llm. It demonstrates the compiler is wired correctly.\n\n## Observation\n\nWhen you see this, the compiler → storage → review flow works.",
                "reasoning": "Generated by mock for smoke testing the compiler pipeline.",
                "source_entries": ["mock-source"]
            },
            {
                "type": "observation",
                "target_file": None,
                "section": None,
                "title": None,
                "content": "Your vault currently has no filled-in identity files. Consider replacing the guidance prompts in me.md with real answers.",
                "reasoning": "Test observation — validates the observation type flow.",
                "source_entries": ["vault:me.md"]
            }
        ]
    })


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_llm_response(raw: str) -> dict:
    """Parse the LLM's JSON response, handling common format slips.

    Returns {"proposals": [...], "error": ...}. Never raises.
    """
    if not raw or not raw.strip():
        return {"proposals": [], "error": "empty LLM response"}

    text = raw.strip()

    # Strip markdown code fences if the LLM added them
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]  # drop the opening ``` line
        if text.endswith("```"):
            text = text[:-3].strip()
        # drop language tag if present
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        return {"proposals": [], "error": f"LLM returned invalid JSON: {e}"}

    if not isinstance(parsed, dict) or "proposals" not in parsed:
        return {"proposals": [], "error": "LLM response missing 'proposals' key"}

    proposals = parsed.get("proposals", [])
    if not isinstance(proposals, list):
        return {"proposals": [], "error": "'proposals' is not a list"}

    # Basic validation of each proposal
    valid = []
    for i, p in enumerate(proposals):
        if not isinstance(p, dict):
            continue
        if p.get("type") not in {"new_concept", "append_to_effort", "observation"}:
            continue
        if not p.get("content"):
            continue
        valid.append(p)

    return {"proposals": valid, "error": parsed.get("error")}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compile journal + vault into proposed updates.")
    parser.add_argument("--days", type=int, default=14, help="Journal lookback window (default: 14)")
    parser.add_argument("--dry-run", action="store_true", help="Show prompt without calling LLM")
    parser.add_argument("--mock-llm", action="store_true", help="Use a fake LLM response (testing)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--tier", default="default", help="AI tier: default|fast|cheap|powerful")
    args = parser.parse_args()

    # Gather data
    journal_data = load_journal_entries(args.days)
    identity = load_vault_identity()

    # Build prompts
    user_prompt = build_user_prompt(journal_data, identity, args.days)

    # Dry-run: show what we'd send
    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print()
        print("=== USER PROMPT ===")
        print(user_prompt)
        sys.exit(0)

    # Call LLM (or mock)
    if args.mock_llm:
        raw_response = mock_llm_response()
    else:
        raw_response = call_llm(SYSTEM_PROMPT, user_prompt, tier=args.tier)

    # Parse
    parsed = parse_llm_response(raw_response)

    if parsed.get("error"):
        _emit({"success": False, "error": parsed["error"], "proposals_stored": 0}, args.format)
        sys.exit(1)

    # Store proposals
    run_id = str(uuid.uuid4())[:8]
    conn = init_db()
    stored_ids = []
    for p in parsed["proposals"]:
        try:
            pid = add_proposal(conn, run_id, p)
            stored_ids.append(pid)
        except ValueError:
            continue  # skip invalid types
    conn.close()

    result = {
        "success": True,
        "run_id": run_id,
        "proposals_stored": len(stored_ids),
        "proposal_ids": stored_ids,
        "journal_entries_read": journal_data.get("count", 0),
        "vault_available": identity.get("available", False),
    }

    _emit(result, args.format)
    sys.exit(0)


def _emit(result: dict, fmt: str):
    if fmt == "json":
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"Compiler run complete.")
            print(f"  Run ID: {result.get('run_id')}")
            print(f"  Journal entries read: {result.get('journal_entries_read')}")
            print(f"  Vault available: {result.get('vault_available')}")
            print(f"  Proposals stored: {result.get('proposals_stored')}")
            if result.get("proposals_stored"):
                print()
                print(f"Review with: python3 .claude/skills/compiler/scripts/review.py list")
        else:
            print(f"Compiler failed: {result.get('error')}", file=sys.stderr)


if __name__ == "__main__":
    main()
