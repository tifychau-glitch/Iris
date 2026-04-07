#!/usr/bin/env python3
"""Test Slack bot token by calling auth.test."""
import json, os, urllib.request
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

token = os.getenv("SLACK_BOT_TOKEN", "")
if not token:
    print(json.dumps({"success": False, "error": "SLACK_BOT_TOKEN not set"}))
    exit()

try:
    req = urllib.request.Request(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if data.get("ok"):
        print(json.dumps({"success": True, "message": f"Slack OK. Team: {data.get('team', '?')}"}))
    else:
        print(json.dumps({"success": False, "error": data.get("error", "Unknown error")}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
