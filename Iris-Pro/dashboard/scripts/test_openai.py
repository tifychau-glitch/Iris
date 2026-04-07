#!/usr/bin/env python3
"""Test OpenAI API key with a minimal request."""
import json, os, urllib.request
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    print(json.dumps({"success": False, "error": "OPENAI_API_KEY not set"}))
    exit()

try:
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    data = json.loads(urllib.request.urlopen(req, timeout=10).read())
    count = len(data.get("data", []))
    print(json.dumps({"success": True, "message": f"OpenAI OK. {count} models available."}))
except urllib.error.HTTPError as e:
    if e.code == 401:
        print(json.dumps({"success": False, "error": "Invalid API key"}))
    else:
        print(json.dumps({"success": False, "error": f"HTTP {e.code}: {e.reason}"}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
