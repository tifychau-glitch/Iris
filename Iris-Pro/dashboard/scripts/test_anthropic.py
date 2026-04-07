#!/usr/bin/env python3
"""Test Anthropic API key by listing models."""
import json, os, urllib.request
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

key = os.getenv("ANTHROPIC_API_KEY", "")
if not key:
    print(json.dumps({"success": False, "error": "ANTHROPIC_API_KEY not set"}))
    exit()

if not key.startswith("sk-ant-"):
    print(json.dumps({"success": False, "error": "Key should start with sk-ant-"}))
    exit()

try:
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
    count = len(data.get("data", []))
    print(json.dumps({"success": True, "message": f"Anthropic OK. {count} models available."}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
