# Memory Directory

3-tier persistent memory system.

## Tier 1: Core Memory — MEMORY.md
- Always loaded into the system prompt at session start
- Contains curated facts, preferences, goals, learned behaviors
- Maximum ~200 lines to stay within token budget
- Updated by the AI during conversations

## Tier 2: Session Memory — logs/
- Daily append-only markdown files (YYYY-MM-DD.md)
- Timeline of events, decisions, completed tasks
- Read at session start for continuity
- Weekly review skill reads 7 days of these for patterns

## Tier 3 (Optional): Long-Term Memory — mem0 + Pinecone
- Cloud-stored vector memory with semantic search
- Automatic fact extraction and deduplication
- See docs/MEMORY-UPGRADE.md for setup instructions
- Cost: ~$0.04/month
