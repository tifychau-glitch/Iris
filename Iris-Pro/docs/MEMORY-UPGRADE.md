# Memory Upgrade: mem0 + Pinecone (Tier 3)

Upgrade from basic memory (MEMORY.md + daily logs) to a full vector memory system with automatic fact extraction, deduplication, and semantic search.

## What You Get

| Feature | Basic (Default) | Upgraded (mem0) |
|---------|----------------|-----------------|
| Persistent facts | MEMORY.md (manual) | Auto-extracted from conversations |
| Session history | Daily logs | Daily logs + vector search |
| Deduplication | Manual | Automatic (ADD/UPDATE/DELETE/NOOP) |
| Search | Read the file | Semantic search (meaning-based) |
| Storage | Local files | Cloud vectors (Pinecone free tier) |
| Cost | $0/month | ~$0.04/month |

## Architecture

```
+----------------------------------------------------------+
|  TIER 1: CORE MEMORY — memory/MEMORY.md                  |
|  Always loaded. Synced from mem0.                        |
+----------------------------------------------------------+
          |
          v
+----------------------------------------------------------+
|  TIER 2: SESSION MEMORY — memory/logs/YYYY-MM-DD.md      |
|  Daily logs. Timeline of events.                         |
+----------------------------------------------------------+
          |
          v
+----------------------------------------------------------+
|  TIER 3: LONG-TERM MEMORY — mem0 + Pinecone              |
|  Every fact as vectors. Semantic search.                 |
|  Auto-dedup. Cloud-stored. Free tier available.          |
+----------------------------------------------------------+
```

## How Deduplication Works

```
New fact: "User likes dark mode"
        |
        v
Search Pinecone for similar memories
        |
+--Found similar--+--------Not found--------+
|                  |                          |
v                  v                          v
"User likes        "User prefers             ADD as new
 light mode"        dark themes"              memory
|                  |
v                  v
DELETE             UPDATE
(contradicts)      (refines)
```

Four outcomes per fact:
- **ADD** — Brand new. Store it.
- **UPDATE** — Overlaps. Merge them.
- **DELETE** — Contradicts. Remove the old one.
- **NOOP** — Already captured. Skip.

## Prerequisites

- Python 3.9+
- OpenAI API key (for GPT-4.1 Nano extraction + embeddings)
- Pinecone API key (free at app.pinecone.io — one API key, no index pausing)

## Quick Setup

The easiest way to install the full memory system:

```bash
python3 setup_memory.py --user-id "your_name" --pinecone-index "your-memory-index"
```

Use `--dry-run` to preview changes first. Use `--help` for all options.

The installer:
1. Installs pip dependencies (mem0ai, pyyaml, python-dotenv, requests, openai, pinecone)
2. Writes `MEM0_USER_ID` to your `.env`
3. Updates the Pinecone index name in the config
4. Switches the Stop hook from basic to advanced (auto-capture)
5. Creates required directories
6. Initializes the FTS5 search index

**Or** the iris-setup wizard will offer to set this up during onboarding if you have the API keys.

## Manual Setup

If you prefer to configure manually:

### 1. Install Dependencies

```bash
pip3 install mem0ai pyyaml python-dotenv requests openai pinecone
```

### 2. Add API Keys to .env

```bash
OPENAI_API_KEY=sk-your-openai-key
PINECONE_API_KEY=your-pinecone-api-key
MEM0_USER_ID=your_name
```

### 3. Create Your Pinecone Index

At [app.pinecone.io](https://app.pinecone.io), create a serverless index:
- **Name:** `iris-memory` (or match whatever you set in the config)
- **Dimensions:** `1536` (matches text-embedding-3-small)
- **Metric:** `cosine`
- **Cloud:** AWS us-east-1 (free tier)

### 4. Configuration

The mem0 config is at `.claude/skills/memory/references/mem0_config.yaml`. The defaults work out of the box. To customize the Pinecone index name:

```yaml
vector_store:
  provider: "pinecone"
  config:
    collection_name: "your-custom-name"  # Change this (mem0 calls this collection_name)
    embedding_model_dims: 1536
    api_key: "${PINECONE_API_KEY}"
```

### 5. Enable the Advanced Stop Hook

Update `.claude/settings.local.json` — replace the basic Stop hook:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/skills/memory/scripts/auto_capture.py",
            "timeout": 60,
            "async": true
          }
        ]
      }
    ]
  }
}
```

### 6. Initialize the Search Index

```bash
python3 .claude/skills/memory/scripts/smart_search.py --rebuild-index
```

## Usage

```bash
# Search memory (smart — recommended)
python3 .claude/skills/memory/scripts/smart_search.py --query "what tools does user prefer" --limit 5

# Search memory (basic vector only)
python3 .claude/skills/memory/scripts/mem0_search.py --query "API rate limits" --limit 10

# Add a memory manually
python3 .claude/skills/memory/scripts/mem0_add.py --content "User prefers Pinecone for vectors"

# Sync to MEMORY.md
python3 .claude/skills/memory/scripts/mem0_sync_md.py

# List all memories
python3 .claude/skills/memory/scripts/mem0_list.py --limit 50

# Delete a memory
python3 .claude/skills/memory/scripts/mem0_delete.py --memory-id "abc123"

# Append to daily log
python3 .claude/skills/memory/scripts/daily_log.py --content "Set up memory system" --type event
```

## Memory Scripts

All scripts are in `.claude/skills/memory/scripts/`:

| Script | Purpose |
|--------|---------|
| `mem0_client.py` | Shared factory + secret sanitizer (all scripts import this) |
| `auto_capture.py` | Stop hook — automatic fact extraction from conversations |
| `smart_search.py` | Enhanced hybrid BM25+vector search with temporal decay + MMR diversity |
| `mem0_search.py` | Basic vector-only search |
| `mem0_add.py` | Manual memory addition with FTS5 indexing |
| `mem0_list.py` | List all memories (fallback to history DB) |
| `mem0_delete.py` | Delete by ID or bulk delete |
| `mem0_sync_md.py` | Sync mem0 to human-readable MEMORY.md via GPT classification |
| `daily_log.py` | Append entries to daily session logs |

## Cost

| Component | Monthly Cost |
|-----------|-------------|
| GPT-4.1 Nano (extraction) | ~$0.03 |
| Embeddings (text-embedding-3-small) | ~$0.006 |
| Pinecone (free tier) | $0.00 |
| SQLite (local) | $0.00 |
| **Total** | **~$0.04** |

## Storage Longevity

```
Pinecone free tier: one serverless index, 2GB storage, no pausing

At 20 facts/day:  years of headroom before hitting storage caps
At 60 facts/day:  still years — dedup keeps growth slow

With dedup, real growth is slower — many facts merge
rather than creating new vectors.
```
