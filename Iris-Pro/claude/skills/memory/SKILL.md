---
name: memory
description: Manage persistent memory (mem0 + Pinecone) — search, add, sync, list, delete
---

# Memory Skill

Manages the 3-tier persistent memory system: mem0 + Pinecone vectors, session logs, and MEMORY.md.

## Python Path

All scripts use: `python3` (or the Python binary on your system)
Scripts location: `.claude/skills/memory/scripts/`

## Operations

### Search memories (smart — recommended)
```bash
python3 .claude/skills/memory/scripts/smart_search.py --query "topic" --limit 5
```
Enhanced retrieval: hybrid BM25+vector search, temporal decay (recent memories rank higher), MMR diversity (avoids redundant results). First run requires `--rebuild-index` to populate the FTS5 keyword index.

### Search memories (basic vector only)
```bash
python3 .claude/skills/memory/scripts/mem0_search.py --query "topic" --limit 10
```

### Rebuild keyword index
```bash
python3 .claude/skills/memory/scripts/smart_search.py --rebuild-index
```
Repopulates the FTS5 keyword index from the history DB. Run once after installation, or periodically to fix drift.

### Add a specific fact
```bash
python3 .claude/skills/memory/scripts/mem0_add.py --content "User prefers Pinecone over Supabase for vectors"
```

### Add from conversation messages
```bash
python3 .claude/skills/memory/scripts/mem0_add.py --messages '[{"role":"user","content":"I switched to ClickUp"}]'
```

### Append to daily session log
```bash
python3 .claude/skills/memory/scripts/daily_log.py --content "Completed memory system overhaul" --type event
```

### Sync mem0 to MEMORY.md
```bash
python3 .claude/skills/memory/scripts/mem0_sync_md.py           # Regenerate MEMORY.md from mem0
python3 .claude/skills/memory/scripts/mem0_sync_md.py --dry-run  # Preview changes
```

### List all memories
```bash
python3 .claude/skills/memory/scripts/mem0_list.py --limit 50
```

### Delete a memory
```bash
python3 .claude/skills/memory/scripts/mem0_delete.py --memory-id "abc123"
python3 .claude/skills/memory/scripts/mem0_delete.py --all --confirm
```

## Architecture

**Three tiers:**
1. **Core Memory** — `memory/MEMORY.md`, always in system prompt, synced from mem0
2. **Session Memory** — Daily logs in `memory/logs/`, human-readable session continuity
3. **Long-Term Memory** — mem0 + Pinecone vectors, automatic extraction + semantic search

**Auto-capture:** Runs via Claude Code Stop hook (`auto_capture.py`). After every response cycle, reads new transcript messages, feeds to mem0 for fact extraction + dedup. No manual intervention needed. Logs at `data/auto_capture.log`.

## Config

- mem0 config: `.claude/skills/memory/references/mem0_config.yaml`
- LLM: GPT-4.1 Nano (extraction + classification)
- Embeddings: text-embedding-3-small
- Vector store: Pinecone (cloud, free tier, serverless)
- History DB: `data/mem0_history.db` (SQLite, auto-managed)
- Capture markers: `data/capture_markers/` (tracks transcript position per session)

## Security

**What's protected:**
- `sanitize_text()` in `mem0_client.py` strips secrets (API keys, tokens, JWTs, connection strings) from all text before it leaves your machine
- Applied in both `auto_capture.py` (automatic) and `mem0_add.py` (manual)
- The extraction prompt explicitly tells GPT-4.1 Nano to skip passwords, keys, tokens, and credentials
- `prepare_messages()` strips code blocks before sending to OpenAI
- System tags/reminders are stripped from transcripts
- `.gitignore` excludes `.env`, `data/`, `memory/logs/`, `.claude/settings.local.json`

**What to be aware of:**
- Conversation snippets are sent to OpenAI API for fact extraction (their API policy: not used for training)
- Extracted facts + vectors are stored in Pinecone cloud
- Local files (SQLite, MEMORY.md, logs) are plaintext on disk
- If working under NDA, be mindful that the system processes all conversation content
- For maximum security: swap to local Qdrant + local LLM (mem0 config supports this as a one-line change per component)

## Known Issues

1. **mem0 v1.0.4 + Pinecone**: `get_all()` and `delete_all()` have bugs. The list and delete scripts fall back to the history DB. Will be fixed in future mem0 releases.
2. **Complex markdown content**: GPT-4.1 Nano sometimes fails to return valid JSON when processing messages with heavy markdown. The `prepare_messages()` function strips most of this, but some batches may still fail. Those messages aren't lost — they're in the transcript.
3. **First run with large backlog**: If auto_capture runs for the first time on a long conversation, it processes everything. Some batches may fail on complex content. Normal incremental runs (2-4 messages) work reliably.
