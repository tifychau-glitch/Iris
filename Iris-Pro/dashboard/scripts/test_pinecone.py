#!/usr/bin/env python3
"""Test Pinecone credentials and verify the specified index exists."""
import json, os, urllib.request
from pathlib import Path
from dotenv import load_dotenv

env_path = os.environ.get("DOTENV_PATH", str(Path(__file__).parent.parent.parent / ".env"))
load_dotenv(env_path)

api_key = os.getenv("PINECONE_API_KEY", "")
index_name = os.getenv("PINECONE_INDEX_NAME", "")

if not api_key:
    print(json.dumps({"success": False, "error": "PINECONE_API_KEY not set"}))
    exit()

# Step 1: Test API key by listing indexes
try:
    req = urllib.request.Request(
        "https://api.pinecone.io/indexes",
        headers={"Api-Key": api_key, "X-Pinecone-API-Version": "2024-07"},
    )
    data = json.loads(urllib.request.urlopen(req, timeout=5).read())
    indexes = [i.get("name") for i in data.get("indexes", [])]
except Exception as e:
    print(json.dumps({"success": False, "error": f"Pinecone connection failed: {e}"}))
    exit()

# Step 2: Verify the named index exists (if provided)
if index_name and index_name not in indexes:
    print(json.dumps({
        "success": False,
        "error": f"Index '{index_name}' not found. Available indexes: {indexes or 'none yet'}"
    }))
    exit()

if not index_name:
    print(json.dumps({
        "success": True,
        "message": f"Pinecone API key valid. No index name set — add PINECONE_INDEX_NAME to finish setup."
    }))
    exit()

print(json.dumps({
    "success": True,
    "message": f"Pinecone connected. Index '{index_name}' found and ready."
}))
