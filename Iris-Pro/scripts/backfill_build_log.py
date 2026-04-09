#!/usr/bin/env python3
"""
Extract user messages and meaningful assistant actions from all Iris-related
Claude Code session logs. Output is a lightweight JSON dump for synthesis.

Usage:
    python3 scripts/backfill_build_log.py

Output:
    .tmp/build-log-raw.json        - full structured extraction
    .tmp/build-log-summary.txt     - human-readable overview per session
"""
import json
import re
from pathlib import Path
from collections import defaultdict

PROJECTS_DIR = Path.home() / ".claude" / "projects"
OUTPUT_DIR = Path(__file__).parent.parent / ".tmp"
OUTPUT_DIR.mkdir(exist_ok=True)

# All Iris-related project folders
IRIS_FOLDERS = [
    "-Users-tiffanychau-Desktop-iris-landing-page",
    "-Users-tiffanychau-Downloads-AI---Automation-Tools-AI-Transformation-Academy-AIOS-Iris-Core",
    "-Users-tiffanychau-Downloads-IRIS",
    "-Users-tiffanychau-Downloads-IRIS-Iris-AI-OS-Template",
    "-Users-tiffanychau-Downloads-IRIS-Iris-Pro",
    "-Users-tiffanychau-Downloads-IRIS-Iris-Pro-2",
    "-Users-tiffanychau-Downloads-iris-product",
]

# Noise filters — skip messages that start with these markers
NOISE_PREFIXES = (
    "<scheduled-task",
    "<system-reminder>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<user-prompt-submit-hook>",
    "<bash-stdout>",
    "<bash-stderr>",
    "Caveat: The messages",
    "[Request interrupted",
    "API Error",
)

# Tool names that count as "actions" (concrete changes to files/system)
ACTION_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}
# Bash commands that are noise (read-only / discovery)
BASH_NOISE_PATTERNS = [
    r"^(ls|cat|head|tail|grep|rg|find|pwd|which|echo|wc|du|df|stat|file)\b",
    r"^git (status|log|diff|show|branch)\b",
    r"^(python3?|node) .* --help",
    r"^curl -s.*head",
]
BASH_NOISE_RE = re.compile("|".join(BASH_NOISE_PATTERNS))


def extract_text(content):
    """Extract plain text from a message's content field (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # Skip tool results — they're not user intent
                    pass
        return "\n".join(p for p in parts if p).strip()
    return ""


def is_noise_user_msg(text):
    """Is this user message noise (system-generated, not a real human message)?"""
    if not text or not text.strip():
        return True
    stripped = text.strip()
    for prefix in NOISE_PREFIXES:
        if stripped.startswith(prefix):
            return True
    # Tool-only results (no real text)
    if stripped.startswith("<") and stripped.endswith(">") and len(stripped) < 200:
        return True
    return False


def extract_tool_uses(content):
    """Pull tool_use blocks from an assistant message's content list."""
    if not isinstance(content, list):
        return []
    uses = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            uses.append({
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            })
    return uses


def summarize_action(tool_use):
    """Convert a tool_use into a short action description, or None if noise."""
    name = tool_use["name"]
    inp = tool_use.get("input", {})
    if name == "Write":
        path = inp.get("file_path", "")
        return f"Write {path}" if path else None
    if name in ("Edit", "MultiEdit"):
        path = inp.get("file_path", "")
        return f"Edit {path}" if path else None
    if name == "NotebookEdit":
        path = inp.get("notebook_path", "")
        return f"NotebookEdit {path}" if path else None
    if name == "Bash":
        cmd = inp.get("command", "").strip()
        if not cmd or BASH_NOISE_RE.match(cmd):
            return None
        # Keep first line, truncate
        first_line = cmd.split("\n")[0]
        return f"Run: {first_line[:140]}"
    return None


def process_session_file(path):
    """Parse one JSONL file and return (user_msgs, actions, first_ts, last_ts)."""
    user_msgs = []
    actions = []
    first_ts = None
    last_ts = None

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = obj.get("timestamp", "")
                if ts:
                    if not first_ts or ts < first_ts:
                        first_ts = ts
                    if not last_ts or ts > last_ts:
                        last_ts = ts

                rec_type = obj.get("type")
                msg = obj.get("message", {})

                if rec_type == "user":
                    text = extract_text(msg.get("content", ""))
                    if not is_noise_user_msg(text):
                        user_msgs.append({
                            "ts": ts,
                            "text": text[:2000],  # cap length
                        })

                elif rec_type == "assistant":
                    tool_uses = extract_tool_uses(msg.get("content", []))
                    for tu in tool_uses:
                        summary = summarize_action(tu)
                        if summary:
                            actions.append({
                                "ts": ts,
                                "action": summary,
                            })

    except Exception as e:
        print(f"  ! error reading {path.name}: {e}")

    return user_msgs, actions, first_ts, last_ts


def main():
    all_sessions = []
    totals = defaultdict(int)

    for folder_name in IRIS_FOLDERS:
        folder = PROJECTS_DIR / folder_name
        if not folder.exists():
            continue
        jsonl_files = sorted(folder.glob("*.jsonl"))
        print(f"\n[{folder_name}] {len(jsonl_files)} session(s)")
        for jf in jsonl_files:
            user_msgs, actions, first_ts, last_ts = process_session_file(jf)
            if not user_msgs and not actions:
                continue
            session_data = {
                "folder": folder_name,
                "session_id": jf.stem,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "user_msg_count": len(user_msgs),
                "action_count": len(actions),
                "user_msgs": user_msgs,
                "actions": actions,
            }
            all_sessions.append(session_data)
            totals["sessions"] += 1
            totals["user_msgs"] += len(user_msgs)
            totals["actions"] += len(actions)
            print(f"  {jf.stem[:8]}  {first_ts[:10] if first_ts else '?'}  {len(user_msgs)} msgs, {len(actions)} actions")

    # Sort sessions chronologically by first_ts
    all_sessions.sort(key=lambda s: s["first_ts"] or "")

    # Write full JSON dump
    raw_out = OUTPUT_DIR / "build-log-raw.json"
    with open(raw_out, "w") as f:
        json.dump(all_sessions, f, indent=2, default=str)

    # Write human-readable summary
    summary_out = OUTPUT_DIR / "build-log-summary.txt"
    with open(summary_out, "w") as f:
        f.write(f"Total sessions: {totals['sessions']}\n")
        f.write(f"Total user messages: {totals['user_msgs']}\n")
        f.write(f"Total actions: {totals['actions']}\n\n")
        for s in all_sessions:
            date = (s["first_ts"] or "")[:10]
            f.write(f"--- {date}  {s['session_id'][:8]}  [{s['folder'][-30:]}]  "
                    f"{s['user_msg_count']} msgs / {s['action_count']} actions ---\n")
            # First 3 user messages as a preview of what the session was about
            for msg in s["user_msgs"][:3]:
                preview = msg["text"].replace("\n", " ")[:200]
                f.write(f"  > {preview}\n")
            f.write("\n")

    print(f"\n{'='*60}")
    print(f"Sessions with content: {totals['sessions']}")
    print(f"Total user messages:   {totals['user_msgs']}")
    print(f"Total actions:         {totals['actions']}")
    print(f"\nRaw dump:  {raw_out}")
    print(f"Summary:   {summary_out}")


if __name__ == "__main__":
    main()
