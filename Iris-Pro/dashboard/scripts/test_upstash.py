#!/usr/bin/env python3
"""Test Upstash Vector credentials and OpenAI embeddings key (required by mem0)."""
import json, os, urllib.request
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

url = os.getenv("UPSTASH_VECTOR_REST_URL", "")
token = os.getenv("UPSTASH_VECTOR_REST_TOKEN", "")

if not url or not token:
    print(json.dumps({"success": False, "error": "UPSTASH_VECTOR_REST_URL or TOKEN not set"}))
    exit()

# Step 1: Test Upstash Vector connection
try:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/info",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
    count = data.get("result", {}).get("vectorCount", "?")
except Exception as e:
    print(json.dumps({"success": False, "error": f"Upstash connection failed: {e}"}))
    exit()

# Step 2: Check OpenAI key (mem0 needs it for embeddings)
openai_key = os.getenv("OPENAI_API_KEY", "")
if not openai_key:
    print(json.dumps({
        "success": True,
        "message": f"Upstash Vector OK ({count} vectors). Warning: OPENAI_API_KEY not set — memory search/save will fail. Set it in the OpenAI connector."
    }))
    exit()

# Step 3: Validate OpenAI key can access embeddings
try:
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {openai_key}"},
    )
    urllib.request.urlopen(req, timeout=5)
except Exception as e:
    print(json.dumps({
        "success": True,
        "message": f"Upstash Vector OK ({count} vectors). Warning: OpenAI key may be invalid — memory features may not work."
    }))
    exit()

print(json.dumps({
    "success": True,
    "message": f"Upstash Vector OK ({count} vectors). OpenAI embeddings ready."
}))
