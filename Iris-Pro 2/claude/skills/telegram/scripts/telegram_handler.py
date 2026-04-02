"""
Telegram → Claude Code Handler — Core daemon with mem0 memory integration.

Routes Telegram messages to Claude Code for execution:
1. Polls Telegram for incoming messages
2. Validates sender (whitelist, rate limits, blocked patterns)
3. Loads relevant memories from Pinecone via mem0
4. Invokes Claude Code with message + memory context
5. Sends response back via Telegram
6. Captures conversation into mem0 for future recall

Usage:
    python .claude/skills/telegram/scripts/telegram_handler.py                    # Start daemon
    python .claude/skills/telegram/scripts/telegram_handler.py --once             # Process one batch
    python .claude/skills/telegram/scripts/telegram_handler.py --test "message"   # Test without Telegram
    python .claude/skills/telegram/scripts/telegram_handler.py --dry-run          # Show what would happen

Env Vars:
    TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY
"""

import os
import sys
import json
import argparse
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _find_project_root():
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = _find_project_root()
SKILL_DIR = Path(__file__).resolve().parent.parent
MEMORY_SCRIPTS = PROJECT_ROOT / ".claude" / "skills" / "memory" / "scripts"

load_dotenv(PROJECT_ROOT / ".env")

# Import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from telegram_send import send_message, send_typing_action
from telegram_bot import (
    poll_once, is_user_allowed, is_rate_limited,
    is_blocked_content, requires_confirmation, load_config,
)
from message_db import log_message, get_history, update_status

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_RESPONSE_LENGTH = 4000  # Telegram message limit
CLAUDE_TIMEOUT = 600  # 10 minutes
PROGRESS_UPDATE_INTERVAL = 45  # Send progress update every N seconds
CONVERSATION_HISTORY_LIMIT = 20


# ---------------------------------------------------------------------------
# Silence handling — timed follow-ups when user doesn't respond
# ---------------------------------------------------------------------------

class SilenceTracker:
    """
    Tracks when IRIS sent a hook message and the user hasn't responded.
    Sends timed follow-ups per the CLAUDE.md silence handling rules.
    """

    def __init__(self):
        # {chat_id: {"hook_sent_at": datetime, "follow_ups_sent": int}}
        self.waiting = {}

    def mark_hook_sent(self, chat_id: int):
        """Call after IRIS sends a message matching a trigger pattern."""
        self.waiting[chat_id] = {
            "hook_sent_at": datetime.now(),
            "follow_ups_sent": 0,
        }

    def mark_user_responded(self, chat_id: int):
        """Call when the user sends any message — clears the silence timer."""
        self.waiting.pop(chat_id, None)

    def check_and_send(self, config: Dict[str, Any]) -> None:
        """
        Check all waiting chats and send follow-ups if enough time has passed.
        Called on every poll cycle.
        """
        silence_config = config.get("silence_handling", {})
        if not silence_config.get("enabled", False):
            return

        follow_ups = silence_config.get("follow_ups", [])
        max_follow_ups = silence_config.get("max_follow_ups", 2)

        now = datetime.now()
        to_remove = []

        for chat_id, state in self.waiting.items():
            sent = state["follow_ups_sent"]

            if sent >= max_follow_ups or sent >= len(follow_ups):
                to_remove.append(chat_id)
                continue

            next_follow_up = follow_ups[sent]
            delay = timedelta(seconds=next_follow_up["delay_seconds"])
            elapsed = now - state["hook_sent_at"]

            if elapsed >= delay:
                message = next_follow_up["message"]
                send_message(chat_id, message)

                log_message(
                    platform="telegram",
                    direction="outbound",
                    chat_id=str(chat_id),
                    content=message,
                    metadata={"type": "silence_follow_up", "follow_up_number": sent + 1},
                )

                state["follow_ups_sent"] = sent + 1
                print(
                    f"[{now.strftime('%H:%M:%S')}] Silence follow-up #{sent + 1} "
                    f"to chat {chat_id}: {message}"
                )

        for chat_id in to_remove:
            del self.waiting[chat_id]

    def should_track_message(self, outbound_text: str, config: Dict[str, Any]) -> bool:
        """Check if an outbound message matches a trigger pattern."""
        silence_config = config.get("silence_handling", {})
        if not silence_config.get("enabled", False):
            return False

        patterns = silence_config.get("trigger_patterns", [])
        text_lower = outbound_text.lower()
        return any(p.lower() in text_lower for p in patterns)


# Global instance
silence_tracker = SilenceTracker()


# ---------------------------------------------------------------------------
# Memory integration (mem0 + Pinecone)
# ---------------------------------------------------------------------------

def get_memory_context(user_message: str) -> str:
    """
    Search mem0/Pinecone for memories relevant to the user's message.
    This is the auto-load feature: every Telegram message triggers a semantic search.
    """
    try:
        sys.path.insert(0, str(MEMORY_SCRIPTS))
        from smart_search import smart_search

        results = smart_search(user_message, limit=5)

        memories = []
        if isinstance(results, dict):
            for item in results.get("results", []):
                mem = item.get("memory", "")
                if mem:
                    memories.append(mem)
        elif isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    mem = item.get("memory", "")
                    if mem:
                        memories.append(mem)

        if not memories:
            return ""

        formatted = "\n".join(f"- {m}" for m in memories)
        return f"<persistent_memory>\nRelevant memories about this user:\n{formatted}\n</persistent_memory>\n\n"

    except Exception as e:
        print(f"Warning: Memory search failed: {e}")
        return ""


def capture_to_memory(user_msg: str, assistant_msg: str):
    """
    Feed Telegram conversation into mem0 for fact extraction.
    Closes the loop: Telegram → Pinecone → future Telegram context.
    """
    try:
        sys.path.insert(0, str(MEMORY_SCRIPTS))
        from mem0_add import add_memory

        messages = [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg[:1500]},
        ]
        add_memory(messages=messages, metadata={"source": "telegram"})
    except Exception as e:
        print(f"Warning: Memory capture failed: {e}")


# ---------------------------------------------------------------------------
# Conversation context from message history
# ---------------------------------------------------------------------------

def get_conversation_context(chat_id: str, limit: int = CONVERSATION_HISTORY_LIMIT) -> str:
    try:
        history = get_history(chat_id=chat_id, platform="telegram", limit=limit)
        messages = history.get("messages", [])

        if not messages:
            return ""

        messages = list(reversed(messages))

        lines = ["<conversation_history>", "Previous messages in this conversation:", ""]

        for msg in messages:
            direction = msg.get("direction", "")
            content = msg.get("content", "")[:1000]
            timestamp = msg.get("created_at", "")[:16]

            if direction == "inbound":
                lines.append(f"[{timestamp}] User: {content}")
            else:
                lines.append(f"[{timestamp}] Assistant: {content[:800]}{'...' if len(content) > 800 else ''}")

        lines.append("</conversation_history>")
        lines.append("")
        lines.append("Current request from user:")

        return "\n".join(lines)

    except Exception as e:
        print(f"Warning: Could not load conversation history: {e}")
        return ""


# ---------------------------------------------------------------------------
# Claude Code invocation
# ---------------------------------------------------------------------------

def _clean_env():
    """Build env for Claude subprocess — strip CLAUDECODE to avoid nested-session block."""
    env = {**os.environ, "TERM": "dumb"}
    env.pop("CLAUDECODE", None)
    return env

def find_claude_cli() -> Optional[str]:
    try:
        result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(["which", "npx"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return "npx @anthropic-ai/claude-code"
    except Exception:
        pass

    return None


def invoke_claude_streaming(
    prompt: str,
    chat_id: int,
    timeout: int = CLAUDE_TIMEOUT,
    update_interval: int = PROGRESS_UPDATE_INTERVAL,
) -> Tuple[bool, str]:
    """Invoke Claude Code with streaming output and Telegram progress updates."""
    claude_cmd = find_claude_cli()
    if not claude_cmd:
        return False, "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"

    if claude_cmd.startswith("npx"):
        cmd = claude_cmd.split() + [
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]
    else:
        cmd = [
            claude_cmd,
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--verbose",
        ]

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=_clean_env(),
        )

        output_text = ""
        last_update_time = time.time()
        last_tool = None
        tool_count = 0
        current_activity = "Starting..."
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                process.kill()
                return False, f"Request timed out after {timeout} seconds. Try a simpler request."

            import select
            ready, _, _ = select.select([process.stdout], [], [], 1.0)

            if ready:
                line = process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")

                    if event_type == "assistant":
                        message = event.get("message", {})
                        content = message.get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                output_text = block.get("text", "")
                            elif block.get("type") == "tool_use":
                                tool_name = block.get("name", "unknown")
                                if tool_name != last_tool:
                                    last_tool = tool_name
                                    tool_count += 1
                                    current_activity = f"Using {tool_name}..."

                    elif event_type == "content_block_start":
                        block = event.get("content_block", {})
                        if block.get("type") == "tool_use":
                            tool_name = block.get("name", "tool")
                            last_tool = tool_name
                            tool_count += 1
                            current_activity = f"Using {tool_name}"

                    elif event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            output_text += delta.get("text", "")

                    elif event_type == "result":
                        output_text = event.get("result", output_text)
                        if event.get("is_error"):
                            return False, output_text

                except json.JSONDecodeError:
                    output_text += line + "\n"

            # Periodic progress updates to Telegram
            elapsed = time.time() - last_update_time
            if elapsed >= update_interval:
                send_typing_action(chat_id)

                progress_msg = f"Still working...\n\n"
                progress_msg += f"Time: {int(time.time() - start_time)}s\n"
                if tool_count > 0:
                    progress_msg += f"Tools used: {tool_count}\n"
                if current_activity:
                    progress_msg += f"Current: {current_activity}"

                send_message(chat_id, progress_msg)
                last_update_time = time.time()

            if process.poll() is not None:
                break

        remaining_stdout, _ = process.communicate(timeout=5)
        if remaining_stdout:
            for line in remaining_stdout.strip().split("\n"):
                if line:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "result":
                            output_text = event.get("result", output_text)
                    except json.JSONDecodeError:
                        output_text += line

        output_text = re.sub(r"\x1b\[[0-9;]*m", "", output_text)
        output_text = output_text.strip()

        if not output_text:
            output_text = "(No output from Claude)"

        return process.returncode == 0, output_text

    except Exception as e:
        return False, f"Error invoking Claude: {str(e)}"


def invoke_claude(prompt: str, timeout: int = CLAUDE_TIMEOUT) -> Tuple[bool, str]:
    """Non-streaming fallback."""
    claude_cmd = find_claude_cli()
    if not claude_cmd:
        return False, "Claude Code CLI not found."

    if claude_cmd.startswith("npx"):
        cmd = claude_cmd.split() + ["-p", prompt, "--dangerously-skip-permissions"]
    else:
        cmd = [claude_cmd, "-p", prompt, "--dangerously-skip-permissions"]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_clean_env(),
        )

        output = result.stdout
        if result.stderr and "error" in result.stderr.lower():
            output += f"\n\nErrors:\n{result.stderr}"

        output = re.sub(r"\x1b\[[0-9;]*m", "", output).strip()

        if not output:
            output = "(No output from Claude)"

        return result.returncode == 0, output

    except subprocess.TimeoutExpired:
        return False, f"Request timed out after {timeout} seconds."
    except Exception as e:
        return False, f"Error invoking Claude: {str(e)}"


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def truncate_response(text: str, max_length: int = MAX_RESPONSE_LENGTH) -> str:
    if len(text) <= max_length:
        return text

    truncated = text[:max_length - 100]
    last_newline = truncated.rfind("\n")
    if last_newline > max_length - 500:
        truncated = truncated[:last_newline]

    return truncated + "\n\n... (response truncated)"


def format_response(success: bool, response: str, execution_time: float) -> str:
    time_str = f"{execution_time:.1f}s" if execution_time < 60 else f"{execution_time/60:.1f}m"

    if success:
        footer = f"\n\n---\nCompleted in {time_str}"
    else:
        footer = f"\n\n---\nFailed after {time_str}"

    max_content = MAX_RESPONSE_LENGTH - len(footer) - 10
    content = truncate_response(response, max_content)

    return content + footer


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------

def handle_message(message: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    chat_id = message.get("chat_id")
    text = message.get("text", "")
    username = message.get("username", "unknown")

    result = {
        "chat_id": chat_id,
        "username": username,
        "request": text,
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
    }

    if dry_run:
        result["response"] = f"[DRY RUN] Would invoke Claude with: {text[:100]}..."
        result["success"] = True
        return result

    # Acknowledge receipt
    send_message(chat_id, "Got it! Working on your request...")
    send_typing_action(chat_id)

    # Log incoming request
    db_result = log_message(
        platform="telegram",
        direction="inbound",
        chat_id=str(chat_id),
        content=text,
        username=username,
    )
    inbound_msg_id = db_result.get("message_id")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing @{username}: {text[:50]}...")

    # Build prompt with memory + conversation context
    memory_context = get_memory_context(text)
    conversation_context = get_conversation_context(str(chat_id))

    context_parts = []
    if memory_context:
        context_parts.append(memory_context)
    if conversation_context:
        context_parts.append(conversation_context)

    full_prompt = "".join(context_parts) + text if context_parts else text

    if memory_context:
        print(f"  Memory context loaded ({memory_context.count(chr(10))} lines)")

    start_time = time.time()

    # Invoke Claude with streaming + progress updates
    success, response = invoke_claude_streaming(
        full_prompt,
        chat_id=chat_id,
        timeout=CLAUDE_TIMEOUT,
        update_interval=PROGRESS_UPDATE_INTERVAL,
    )

    execution_time = time.time() - start_time

    # Format and send response
    formatted = format_response(success, response, execution_time)
    send_result = send_message(chat_id, formatted)

    # Check if this response is a hook that should trigger silence tracking
    config = load_config()
    if silence_tracker.should_track_message(response, config):
        silence_tracker.mark_hook_sent(chat_id)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Silence tracker armed for chat {chat_id}")

    # Log outbound response
    log_message(
        platform="telegram",
        direction="outbound",
        chat_id=str(chat_id),
        content=formatted,
    )

    # Update inbound message status
    if inbound_msg_id:
        update_status(inbound_msg_id, "processed" if success else "failed")

    # Capture conversation into mem0 (async-safe — failures don't block response)
    capture_to_memory(text, response)

    result["success"] = success
    result["response"] = response[:500] + "..." if len(response) > 500 else response
    result["execution_time"] = execution_time
    result["sent"] = send_result.get("success", False)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Response sent ({execution_time:.1f}s)")

    return result


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def process_updates(once: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    config = load_config()
    interval = config.get("telegram", {}).get("polling_interval", 2.0)
    silence_enabled = config.get("silence_handling", {}).get("enabled", False)

    print(f"Starting Telegram handler")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Polling interval: {interval}s")
    print(f"  Memory: mem0 + Pinecone (auto-load + auto-capture)")
    print(f"  Silence handling: {'enabled' if silence_enabled else 'disabled'}")
    print(f"  Dry run: {dry_run}")
    print("Press Ctrl+C to stop\n")

    offset = None
    total_processed = 0
    results = []

    try:
        while True:
            poll_result = poll_once(offset)

            if poll_result.get("success"):
                offset = poll_result.get("new_offset", offset)

                for msg_result in poll_result.get("results", []):
                    if msg_result.get("processed") and msg_result.get("text"):
                        # User responded — clear any silence timer for this chat
                        chat_id = msg_result.get("chat_id")
                        if chat_id:
                            silence_tracker.mark_user_responded(chat_id)

                        handle_result = handle_message(msg_result, dry_run=dry_run)
                        results.append(handle_result)
                        total_processed += 1

                        if once:
                            return {
                                "success": True,
                                "processed": total_processed,
                                "results": results,
                            }

            # Check silence timers and send follow-ups if needed
            if not dry_run:
                silence_tracker.check_and_send(config)

            if once and total_processed == 0:
                return {"success": True, "processed": 0, "message": "No pending messages"}

            if not once:
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping handler...")
        return {
            "success": True,
            "processed": total_processed,
            "results": results,
            "stopped": "user_interrupt",
        }


def test_claude(message: str) -> Dict[str, Any]:
    """Test Claude invocation without Telegram."""
    print(f"Testing Claude with: {message}\n")
    print("-" * 50)

    # Also test memory search
    print("Searching memory for context...")
    memory = get_memory_context(message)
    if memory:
        print(f"Found memory context:\n{memory[:300]}")
    else:
        print("No relevant memories found.")
    print("-" * 50)

    start = time.time()
    full_prompt = memory + message if memory else message
    success, response = invoke_claude(full_prompt)
    elapsed = time.time() - start

    print(response)
    print("-" * 50)
    print(f"\nSuccess: {success}")
    print(f"Time: {elapsed:.1f}s")

    return {"success": success, "response": response, "execution_time": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Telegram → Claude Code Handler")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit")
    parser.add_argument("--dry-run", action="store_true", help="Don't invoke Claude")
    parser.add_argument("--test", type=str, metavar="MESSAGE", help="Test Claude without Telegram")
    parser.add_argument("--check", action="store_true", help="Check if Claude CLI is available")

    args = parser.parse_args()

    if args.check:
        claude_cmd = find_claude_cli()
        if claude_cmd:
            print(f"Claude CLI found: {claude_cmd}")
            sys.exit(0)
        else:
            print("Claude CLI not found")
            sys.exit(1)

    if args.test:
        result = test_claude(args.test)
        sys.exit(0 if result["success"] else 1)

    result = process_updates(once=args.once, dry_run=args.dry_run)

    if result.get("processed", 0) > 0:
        print(f"\nProcessed {result['processed']} message(s)")


if __name__ == "__main__":
    main()
