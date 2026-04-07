#!/usr/bin/env python3
"""
generate_brain.py — Compile IRIS context bundle for Claude.ai Project.

Reads from sibling folders (Iris-Pro/, iris-landing-page/) and produces
a bundle in output/ that can be dragged into a Claude.ai Project.

Usage:
    python3 generate_brain.py

This script is personal tooling. It lives OUTSIDE Iris-Pro/ on purpose
so it never ships to customers.
"""

from pathlib import Path
from datetime import datetime
import shutil
import re

# ---------- Paths ----------
BRAIN_DIR = Path(__file__).parent.resolve()
IRIS_ROOT = BRAIN_DIR.parent
IRIS_PRO = IRIS_ROOT / "Iris-Pro"
LANDING = IRIS_ROOT / "iris-landing-page"
OUTPUT = BRAIN_DIR / "output"

TODAY = datetime.now().strftime("%Y-%m-%d")


def read(path: Path) -> str:
    """Read a file, return empty string if missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def extract_section(content: str, header: str) -> str:
    """Extract a markdown section by its ## header until the next ## or ---."""
    pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##\s|\n---|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def recent_daily_logs(limit: int = 3) -> str:
    """Get the most recent daily log entries, condensed."""
    logs_dir = IRIS_PRO / "memory" / "logs"
    if not logs_dir.exists():
        return "_No daily logs found._"

    log_files = sorted(logs_dir.glob("*.md"), reverse=True)[:limit]
    if not log_files:
        return "_No daily logs found._"

    chunks = []
    for log in log_files:
        content = read(log)
        # Strip the header, keep the rest, cap length
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith(">")]
        body = "\n".join(lines[2:])  # skip title + blank
        if len(body) > 800:
            body = body[:800] + "\n_...(truncated)_"
        chunks.append(f"### {log.stem}\n\n{body}")

    return "\n\n".join(chunks)


def build_brain_md() -> str:
    """Compile IRIS-BRAIN.md from source files."""
    business = read(IRIS_PRO / "context" / "my-business.md")
    tracker = read(IRIS_PRO / "TRACKER.md")
    wrestling = read(BRAIN_DIR / "wrestling.md")
    memory = read(IRIS_PRO / "memory" / "MEMORY.md")

    in_progress = extract_section(tracker, "In Progress")
    known_bugs = extract_section(tracker, "Known Bugs")
    phase_1 = extract_section(tracker, r"Phase 1 — MVP \(Current\)")

    # Strip the wrestling.md intro blockquote
    wrestling_body = re.sub(r"^#.*?\n(>.*?\n)*\n", "", wrestling, count=1, flags=re.DOTALL)

    return f"""# IRIS Brain — Strategic State

> Auto-generated snapshot for Claude.ai Project context.
> Last updated: {TODAY}
> Source: generate_brain.py in /Users/tiffanychau/Downloads/IRIS/iris-brain/

---

## What IRIS Is

IRIS is an AI accountability product for solopreneurs. It closes the gap between what people say they'll do and what they actually do. Built by Tiffany — non-technical solo founder — using Claude Code as the development environment.

**Two tiers:**

- **Iris Core** (Free) — Telegram bot on a VPS. Lead magnet. Delivers the "Mount Everest" experience — articulates a 3-5 year north star, kicks off accountability check-ins. Conversation memory currently resets on bot restart (known bug).
- **Iris Pro** ($797 one-time) — Full Claude Code workspace shipped as a zip via Lemon Squeezy. Customers download, install locally, get the complete AI OS: 25 skills, 3-tier memory, dashboard, hooks, the works.

**The offer funnel:** Warm network → Iris Core (free taste) → Iris Pro ($797 upgrade).

---

## Components & Dependencies

**Iris Core (runs on VPS):**
- Python Telegram bot (`bot.py`)
- SQLite for user state
- Deployed and running, needs monitoring
- Bug: conversation memory resets on process restart

**Iris Pro (runs on customer machine):**
- Claude Code workspace (`.claude/skills/`, `context/`, `memory/`, `data/`)
- Local dashboard at `localhost:5050` (Flask + SQLite)
- 3-tier memory: MEMORY.md → daily logs → mem0/Upstash Vector (optional)
- 25 skills, 3 subagents, hooks for safety
- Setup wizard runs on first conversation

**Landing page:**
- Lives in `iris-landing-page/` (separate folder)
- `index.html` — current landing page
- `preorder.html` — preorder flow
- `old-version.html` — previous version kept for reference

**External dependencies:**
- Lemon Squeezy (payments)
- Telegram Bot API (Core)
- Optional: Upstash Vector, OpenAI, Gmail, Slack (Pro connectors)
- Hostinger VPS (Core hosting)

---

## Business Context

{business.strip()}

---

## Active Work (In Progress)

{in_progress or "_Nothing currently in progress._"}

---

## Phase 1 — MVP Roadmap

{phase_1 or "_No Phase 1 items._"}

---

## Known Bugs

{known_bugs or "_No known bugs._"}

---

## Currently Wrestling With

{wrestling_body.strip() or "_No open questions captured. Edit wrestling.md to add some._"}

---

## Recent Activity (Last 3 Daily Logs)

{recent_daily_logs(3)}

---

## Curated Memory (from MEMORY.md)

{memory.strip() or "_No curated memory yet._"}

---

## How to Use This File

This file is the strategic context for brainstorm conversations on Claude.ai. The Claude Project knowledge base also contains:

- `landing-page.html` — current landing page source (reference this for copy/design feedback)
- `dashboard-index.html` — current dashboard UI
- `dashboard-settings.html` — settings page UI
- `my-voice.md` — Tiffany's voice guide (use when drafting copy)

When Tiffany pastes a screenshot, cross-reference it against the HTML files. Give specific, actionable feedback — not vague suggestions.
"""


def copy_assets():
    """Copy HTML and voice files into output/."""
    pairs = [
        (LANDING / "index.html", OUTPUT / "landing-page.html"),
        (IRIS_PRO / "dashboard" / "index.html", OUTPUT / "dashboard-index.html"),
        (IRIS_PRO / "dashboard" / "settings.html", OUTPUT / "dashboard-settings.html"),
        (IRIS_PRO / "context" / "my-voice.md", OUTPUT / "my-voice.md"),
    ]
    copied, missing = [], []
    for src, dst in pairs:
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(dst.name)
        else:
            missing.append(str(src))
    return copied, missing


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Clean old output (but keep the folder)
    for f in OUTPUT.iterdir():
        if f.is_file():
            f.unlink()

    # Write IRIS-BRAIN.md
    brain_path = OUTPUT / "IRIS-BRAIN.md"
    brain_path.write_text(build_brain_md(), encoding="utf-8")

    # Copy assets
    copied, missing = copy_assets()

    # Report
    print(f"[ok] IRIS Brain bundle generated in {OUTPUT}")
    print(f"     - IRIS-BRAIN.md ({brain_path.stat().st_size // 1024} KB)")
    for name in copied:
        size = (OUTPUT / name).stat().st_size // 1024
        print(f"     - {name} ({size} KB)")
    if missing:
        print("\n[warn] Missing source files (skipped):")
        for m in missing:
            print(f"     - {m}")
    print("\nNext: drag contents of output/ into your Claude.ai Project knowledge base.")
    print("      (Delete old files first.)")


if __name__ == "__main__":
    main()
