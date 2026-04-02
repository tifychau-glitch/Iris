"""
Telegram Bot Handler — Polling + security validation.

Usage:
    python .claude/skills/telegram/scripts/telegram_bot.py --poll              # Start polling
    python .claude/skills/telegram/scripts/telegram_bot.py --poll --once       # Check once and exit
    python .claude/skills/telegram/scripts/telegram_bot.py --set-commands      # Register bot commands

Env Vars:
    TELEGRAM_BOT_TOKEN (required)
"""

import sys
import json
import argparse
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import yaml

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
load_dotenv(PROJECT_ROOT / ".env")

# Import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from telegram_send import telegram_api_call, send_message, get_bot_token, log_message

CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "messaging.yaml"

# Rate limiting storage (in-memory)
rate_limits = defaultdict(list)


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def is_user_allowed(user_id: int, username: Optional[str] = None) -> bool:
    config = load_config()
    telegram_config = config.get("telegram", {})

    allowed_ids = telegram_config.get("allowed_user_ids", [])
    allowed_usernames = telegram_config.get("allowed_usernames", [])

    # Secure by default — reject if no whitelist
    if not allowed_ids and not allowed_usernames:
        return False

    if user_id in allowed_ids:
        return True

    if username and username.lower() in [u.lower() for u in allowed_usernames]:
        return True

    return False


def is_rate_limited(user_id: int) -> bool:
    config = load_config()
    security = config.get("security", {})

    max_per_minute = security.get("max_messages_per_minute", 30)
    max_per_hour = security.get("max_messages_per_hour", 200)

    now = datetime.now()
    minute_ago = now - timedelta(minutes=1)
    hour_ago = now - timedelta(hours=1)

    rate_limits[user_id] = [t for t in rate_limits[user_id] if t > hour_ago]

    recent_minute = sum(1 for t in rate_limits[user_id] if t > minute_ago)
    recent_hour = len(rate_limits[user_id])

    if recent_minute >= max_per_minute or recent_hour >= max_per_hour:
        return True

    rate_limits[user_id].append(now)
    return False


def is_blocked_content(text: str) -> Optional[str]:
    config = load_config()
    blocked = config.get("security", {}).get("blocked_patterns", [])

    for pattern in blocked:
        if pattern.lower() in text.lower():
            return pattern

    return None


def requires_confirmation(text: str) -> Optional[str]:
    config = load_config()
    confirm_ops = config.get("security", {}).get("require_confirmation", [])

    text_lower = text.lower()

    for op in confirm_ops:
        if op.lower().replace("_", " ") in text_lower or op.lower() in text_lower:
            return op

    return None


def get_updates(offset: Optional[int] = None, timeout: int = 30) -> Dict[str, Any]:
    data = {
        "timeout": timeout,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset:
        data["offset"] = offset

    return telegram_api_call("getUpdates", data)


def process_message(message: Dict) -> Dict[str, Any]:
    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})
    user_id = user.get("id")
    username = user.get("username")
    text = message.get("text", "")

    result = {
        "message_id": message.get("message_id"),
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "text": text,
        "date": message.get("date"),
        "processed": False,
        "response": None,
    }

    log_message(chat_id, "IN", text)

    if not is_user_allowed(user_id, username):
        result["rejected"] = "not_whitelisted"
        result["response"] = "Unauthorized. Your user ID is not in the whitelist."
        send_message(chat_id, result["response"])
        return result

    if is_rate_limited(user_id):
        result["rejected"] = "rate_limited"
        result["response"] = "Rate limit exceeded. Please wait before sending more messages."
        send_message(chat_id, result["response"])
        return result

    blocked = is_blocked_content(text)
    if blocked:
        result["rejected"] = "blocked_content"
        result["response"] = f"Message blocked: contains prohibited pattern '{blocked}'"
        send_message(chat_id, result["response"])
        return result

    confirm = requires_confirmation(text)
    if confirm:
        result["requires_confirmation"] = confirm
        result["response"] = f"This action ({confirm}) requires confirmation. Reply 'CONFIRM' to proceed."
        send_message(chat_id, result["response"])
        return result

    result["processed"] = True

    if text.startswith("/"):
        result["is_command"] = True
        result["command"] = text.split()[0][1:]

    return result


def process_callback_query(callback: Dict) -> Dict[str, Any]:
    callback_id = callback.get("id")
    user = callback.get("from", {})
    user_id = user.get("id")
    username = user.get("username")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")

    telegram_api_call("answerCallbackQuery", {"callback_query_id": callback_id})

    result = {
        "type": "callback_query",
        "callback_id": callback_id,
        "user_id": user_id,
        "username": username,
        "data": data,
        "chat_id": chat_id,
        "original_message_id": message.get("message_id"),
    }

    if not is_user_allowed(user_id, username):
        result["rejected"] = "not_whitelisted"
        return result

    result["processed"] = True
    return result


def poll_once(offset: Optional[int] = None) -> Dict[str, Any]:
    updates_result = get_updates(offset=offset, timeout=1)

    if not updates_result.get("success"):
        return updates_result

    updates = updates_result.get("result", [])
    results = []
    new_offset = offset

    for update in updates:
        update_id = update.get("update_id")
        new_offset = update_id + 1

        if "message" in update:
            result = process_message(update["message"])
            results.append(result)
        elif "callback_query" in update:
            result = process_callback_query(update["callback_query"])
            results.append(result)

    return {
        "success": True,
        "updates_processed": len(results),
        "results": results,
        "new_offset": new_offset,
    }


def poll_continuous(check_interval: float = 1.0):
    config = load_config()
    interval = config.get("telegram", {}).get("polling_interval", check_interval)

    print(f"Starting Telegram bot polling (interval: {interval}s)")
    print("Press Ctrl+C to stop")

    offset = None

    try:
        while True:
            result = poll_once(offset)

            if result.get("success"):
                offset = result.get("new_offset", offset)

                for msg_result in result.get("results", []):
                    if msg_result.get("processed"):
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"@{msg_result.get('username', 'unknown')}: "
                            f"{msg_result.get('text', msg_result.get('data', ''))[:50]}"
                        )

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopping bot...")


def set_bot_commands() -> Dict[str, Any]:
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "help", "description": "Show help message"},
        {"command": "status", "description": "Check system status"},
        {"command": "memory", "description": "Search memory"},
    ]
    return telegram_api_call("setMyCommands", {"commands": commands})


def main():
    parser = argparse.ArgumentParser(description="Telegram Bot Handler")
    parser.add_argument("--poll", action="store_true", help="Start polling for messages")
    parser.add_argument("--once", action="store_true", help="Poll once and exit (use with --poll)")
    parser.add_argument("--updates", action="store_true", help="Get recent updates without processing")
    parser.add_argument("--set-commands", action="store_true", help="Register bot commands")
    parser.add_argument("--offset", type=int, help="Update offset")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")

    args = parser.parse_args()
    result = None

    if args.set_commands:
        result = set_bot_commands()
    elif args.updates:
        result = get_updates(offset=args.offset, timeout=1)
    elif args.poll:
        if args.once:
            result = poll_once(args.offset)
        else:
            poll_continuous(args.interval)
            return
    else:
        parser.print_help()
        sys.exit(0)

    if result:
        if result.get("success"):
            print("OK")
        else:
            print(f"ERROR {result.get('error')}")
            sys.exit(1)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
