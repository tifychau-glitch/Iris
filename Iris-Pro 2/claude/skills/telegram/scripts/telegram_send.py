"""
Telegram Message Sender — Direct Bot API wrapper.

Usage:
    python .claude/skills/telegram/scripts/telegram_send.py --chat-id 123 --message "Hello!"
    python .claude/skills/telegram/scripts/telegram_send.py --chat-id 123 --file /path/to/file.pdf
    python .claude/skills/telegram/scripts/telegram_send.py --chat-id 123 --message "Pick:" --buttons "Yes,No"

Env Vars:
    TELEGRAM_BOT_TOKEN (required)
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import yaml

# ---------------------------------------------------------------------------
# Paths — resolve relative to project root, not script location
# ---------------------------------------------------------------------------

def _find_project_root():
    """Walk up until we find .env or CLAUDE.md."""
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = _find_project_root()
load_dotenv(PROJECT_ROOT / ".env")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "references" / "messaging.yaml"
LOG_DIR = PROJECT_ROOT / "logs"

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def get_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    return token


def telegram_api_call(method: str, data: Dict = None, files: Dict = None) -> Dict[str, Any]:
    token = get_bot_token()
    url = TELEGRAM_API_BASE.format(token=token, method=method)

    try:
        if files:
            response = requests.post(url, data=data, files=files, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)

        result = response.json()

        if not result.get("ok"):
            return {
                "success": False,
                "error": result.get("description", "Unknown error"),
                "error_code": result.get("error_code"),
            }

        return {"success": True, "result": result.get("result")}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
    disable_notification: bool = False,
    buttons: Optional[List[List[Dict]]] = None,
) -> Dict[str, Any]:
    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_notification": disable_notification,
    }

    if parse_mode:
        data["parse_mode"] = (
            parse_mode.upper() if parse_mode.lower() in ["markdown", "html"] else None
        )

    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id

    if buttons:
        data["reply_markup"] = {"inline_keyboard": buttons}

    result = telegram_api_call("sendMessage", data)

    if result.get("success"):
        msg = result["result"]
        return {
            "success": True,
            "message_id": msg.get("message_id"),
            "chat_id": chat_id,
            "date": msg.get("date"),
            "text": text[:100] + "..." if len(text) > 100 else text,
        }

    return result


def send_document(
    chat_id: int, file_path: str, caption: Optional[str] = None
) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    with open(path, "rb") as f:
        files = {"document": (path.name, f)}
        result = telegram_api_call("sendDocument", data, files)

    if result.get("success"):
        return {
            "success": True,
            "message_id": result["result"].get("message_id"),
            "file_name": path.name,
        }

    return result


def send_photo(
    chat_id: int, photo_path: str, caption: Optional[str] = None
) -> Dict[str, Any]:
    path = Path(photo_path)
    if not path.exists():
        return {"success": False, "error": f"Photo not found: {photo_path}"}

    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    with open(path, "rb") as f:
        files = {"photo": (path.name, f)}
        result = telegram_api_call("sendPhoto", data, files)

    if result.get("success"):
        return {"success": True, "message_id": result["result"].get("message_id")}

    return result


def send_typing_action(chat_id: int) -> Dict[str, Any]:
    return telegram_api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


def create_inline_buttons(button_text: str) -> List[List[Dict]]:
    buttons = []
    row = []

    for item in button_text.split(","):
        item = item.strip()
        if "|" in item:
            text, callback = item.split("|", 1)
            row.append({"text": text.strip(), "callback_data": callback.strip()})
        else:
            row.append({"text": item, "callback_data": item.lower().replace(" ", "_")})

        if len(row) >= 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return buttons


def get_me() -> Dict[str, Any]:
    return telegram_api_call("getMe")


def log_message(chat_id: int, direction: str, text: str):
    config = load_config()
    if not config.get("logging", {}).get("enabled", True):
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "messaging.log"

    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {direction} | chat:{chat_id} | {text[:200]}\n"

    with open(log_file, "a") as f:
        f.write(log_entry)


def main():
    parser = argparse.ArgumentParser(description="Send Telegram messages")
    parser.add_argument("--chat-id", type=int, required=True, help="Telegram chat/user ID")
    parser.add_argument("--message", "-m", help="Message text")
    parser.add_argument("--parse-mode", choices=["markdown", "html"], help="Message formatting")
    parser.add_argument("--file", help="File to send")
    parser.add_argument("--photo", help="Photo to send")
    parser.add_argument("--caption", help="Caption for file/photo")
    parser.add_argument("--buttons", help="Inline buttons (comma-separated)")
    parser.add_argument("--silent", action="store_true", help="Send without notification")
    parser.add_argument("--reply-to", type=int, help="Message ID to reply to")
    parser.add_argument("--bot-info", action="store_true", help="Get bot information")

    args = parser.parse_args()

    result = None

    if args.bot_info:
        result = get_me()
    elif args.file:
        result = send_document(args.chat_id, args.file, args.caption)
        if result.get("success"):
            log_message(args.chat_id, "OUT", f"[FILE] {args.file}")
    elif args.photo:
        result = send_photo(args.chat_id, args.photo, args.caption)
        if result.get("success"):
            log_message(args.chat_id, "OUT", f"[PHOTO] {args.photo}")
    elif args.message:
        buttons = create_inline_buttons(args.buttons) if args.buttons else None
        result = send_message(
            chat_id=args.chat_id,
            text=args.message,
            parse_mode=args.parse_mode,
            reply_to_message_id=args.reply_to,
            disable_notification=args.silent,
            buttons=buttons,
        )
        if result.get("success"):
            log_message(args.chat_id, "OUT", args.message)
    else:
        parser.print_help()
        sys.exit(1)

    if result:
        if result.get("success"):
            print("OK Message sent")
        else:
            print(f"ERROR {result.get('error')}")
            sys.exit(1)

        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
