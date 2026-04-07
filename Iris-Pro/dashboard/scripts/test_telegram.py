#!/usr/bin/env python3
"""Test Telegram bot token, check whitelist, and send test message."""
import json, os, urllib.request, urllib.parse
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not token:
    print(json.dumps({"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}))
    exit()

# Step 1: Validate token with getMe
try:
    data = json.loads(urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/getMe", timeout=5
    ).read())
    if not data.get("ok"):
        print(json.dumps({"success": False, "error": data.get("description", "Unknown error")}))
        exit()
    bot_username = data["result"].get("username", "unknown")
except Exception as e:
    print(json.dumps({"success": False, "error": f"Token validation failed: {e}"}))
    exit()

# Step 2: Check for user ID
user_id = os.getenv("TELEGRAM_USER_ID", "")
if not user_id:
    print(json.dumps({
        "success": True,
        "message": f"Bot @{bot_username} is valid, but no User ID configured. Add your Telegram User ID so the bot can message you."
    }))
    exit()

# Step 3: Send test message
try:
    payload = urllib.parse.urlencode({
        "chat_id": user_id,
        "text": "IRIS connected successfully. You'll receive messages here.",
    }).encode()
    resp = json.loads(urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload, timeout=5
    ).read())
    if resp.get("ok"):
        print(json.dumps({
            "success": True,
            "message": f"Bot @{bot_username} verified and test message sent."
        }))
    else:
        desc = resp.get("description", "Unknown error")
        print(json.dumps({
            "success": True,
            "message": f"Bot @{bot_username} is valid. Could not send test message: {desc}. Make sure you've started a conversation with the bot first."
        }))
except Exception as e:
    print(json.dumps({
        "success": True,
        "message": f"Bot @{bot_username} is valid. Test message failed: {e}. Make sure you've messaged the bot first."
    }))
