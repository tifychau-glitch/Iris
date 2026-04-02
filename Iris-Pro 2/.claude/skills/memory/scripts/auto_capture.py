#!/usr/bin/env python3
"""
Hook: Automatic Memory Capture (Stop event)
Purpose: Reads new messages from the Claude Code conversation transcript
         and feeds them to mem0 for intelligent fact extraction + dedup.

Triggered by: Claude Code "Stop" hook (fires after every response cycle)
Input: JSON on stdin with session_id, transcript_path, cwd
Output: Exit 0 (success) — runs async, no blocking
"""

import json
import logging
import sys
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from mem0_client import PROJECT_ROOT

MARKERS_DIR = PROJECT_ROOT / "data" / "capture_markers"
LOG_FILE = PROJECT_ROOT / "data" / "auto_capture.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("auto_capture")


def read_hook_input():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, IOError) as e:
        log.error(f"Failed to read hook input: {e}")
        return None


def get_marker(session_id):
    marker_file = MARKERS_DIR / f"{session_id}.marker"
    if marker_file.exists():
        try:
            return int(marker_file.read_text().strip())
        except (ValueError, IOError):
            return 0
    return 0


def set_marker(session_id, line_number):
    MARKERS_DIR.mkdir(parents=True, exist_ok=True)
    marker_file = MARKERS_DIR / f"{session_id}.marker"
    marker_file.write_text(str(line_number))


def extract_text_from_content(content):
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        texts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text", "").strip()
                if text.startswith("<system-reminder>") or text.startswith("<ide_"):
                    continue
                if len(text) < 10:
                    continue
                texts.append(text)
        return "\n".join(texts) if texts else ""

    return ""


def strip_system_tags(text):
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    text = re.sub(r"<ide_\w+>.*?</ide_\w+>", "", text, flags=re.DOTALL)
    return text.strip()


def parse_new_messages(transcript_path, start_line):
    messages = []
    current_line = 0

    try:
        with open(transcript_path, "r") as f:
            for i, line in enumerate(f):
                current_line = i + 1
                if i < start_line:
                    continue

                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type")
                if msg_type not in ("user", "assistant"):
                    continue

                msg = obj.get("message", {})
                role = msg.get("role", "")
                content = msg.get("content", "")

                text = extract_text_from_content(content)
                if not text:
                    continue

                text = strip_system_tags(text)
                if not text or len(text) < 15:
                    continue

                messages.append({"role": role, "content": text})

    except (IOError, OSError) as e:
        log.error(f"Failed to read transcript: {e}")

    return messages, current_line


def prepare_messages(messages, max_msg_chars=1500):
    cleaned = []
    for msg in messages:
        text = msg["content"]
        text = re.sub(r"```[\s\S]*?```", "[code block]", text)
        text = re.sub(r"\|.*\|.*\n", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()
        if len(text) > max_msg_chars:
            text = text[:max_msg_chars] + "..."
        if text and len(text) >= 15:
            cleaned.append({"role": msg["role"], "content": text})
    return cleaned


def batch_messages(messages, max_batch_chars=3000):
    batches = []
    current_batch = []
    current_size = 0
    for msg in messages:
        msg_len = len(msg["content"])
        if current_size + msg_len > max_batch_chars and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(msg)
        current_size += msg_len
    if current_batch:
        batches.append(current_batch)
    return batches


def feed_to_mem0(messages):
    from mem0_client import get_memory_client, USER_ID, sanitize_text

    m = get_memory_client()
    cleaned = prepare_messages(messages)
    # Scrub secrets before sending anything to OpenAI/Pinecone
    for msg in cleaned:
        msg["content"] = sanitize_text(msg["content"])
    batches = batch_messages(cleaned)

    total_events = 0
    all_results = []

    for i, batch in enumerate(batches):
        try:
            result = m.add(batch, user_id=USER_ID, metadata={"source": "auto_capture"})
            events = result.get("results", []) if isinstance(result, dict) else []
            total_events += len(events)
            all_results.extend(events)
            log.info(f"  Batch {i+1}/{len(batches)}: {len(events)} events")
        except Exception as e:
            log.error(f"  Batch {i+1}/{len(batches)} failed: {e}")

    return {"results": all_results}


def main():
    hook_input = read_hook_input()
    if not hook_input:
        log.warning("No hook input received, exiting")
        sys.exit(0)

    session_id = hook_input.get("session_id", "unknown")
    transcript_path = hook_input.get("transcript_path", "")

    if not transcript_path or not Path(transcript_path).exists():
        log.warning(f"No transcript at {transcript_path}")
        sys.exit(0)

    log.info(f"Processing session {session_id}")

    start_line = get_marker(session_id)
    messages, end_line = parse_new_messages(transcript_path, start_line)

    if not messages:
        log.info(f"No new messages since line {start_line}")
        set_marker(session_id, end_line)
        sys.exit(0)

    log.info(f"Found {len(messages)} new messages (lines {start_line}-{end_line})")
    log.info(f"Feeding {len(messages)} messages to mem0 (will be cleaned and batched)")

    try:
        result = feed_to_mem0(messages)
        event_count = len(result.get("results", [])) if isinstance(result, dict) else 0
        log.info(f"mem0 processed: {event_count} memory events")
    except Exception as e:
        log.error(f"mem0 extraction failed: {e}")

    set_marker(session_id, end_line)
    log.info(f"Marker updated to line {end_line}")

    sys.exit(0)


if __name__ == "__main__":
    main()
