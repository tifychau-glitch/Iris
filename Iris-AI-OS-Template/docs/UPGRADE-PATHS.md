# Upgrade Paths

The AI OS core works with zero external API keys (just a Claude Code subscription). These upgrades unlock additional capabilities.

## Tier 1: Free Upgrades

### Notion Integration
Connect Notion for notes, databases, and CRM functionality.

1. Go to notion.so/my-integrations
2. Create a new integration
3. Copy the token
4. Add to `.env`: `NOTION_TOKEN=your-token`
5. Add MCP config to `.claude/settings.local.json` (see docs/MCP-SERVERS.md)

### Google Calendar
Access your calendar for scheduling and meeting prep.

1. Create a Google Cloud project
2. Enable Calendar API
3. Create OAuth credentials
4. Add to `.env`
5. Add MCP config

## Tier 2: Paid API Upgrades

### Perplexity (Better Research)
WebSearch works, but Perplexity provides deeper synthesis and better sources.

1. Sign up at perplexity.ai
2. Get an API key
3. Add to `.env`: `PERPLEXITY_API_KEY=your-key`
4. Add MCP config (see docs/MCP-SERVERS.md)

Cost: ~$5/month for moderate use

### Gmail API (Automated Email)
Upgrade the email-assistant from paste-based to automated inbox processing.

1. Create a Google Cloud project
2. Enable Gmail API
3. Create OAuth credentials (Desktop app type)
4. Download `credentials.json` to project root
5. Run the auth flow: `python3 .claude/skills/email-digest/scripts/gmail_auth.py`
6. This creates `token.json` (auto-refreshes)
7. Now the email-digest skill can fetch emails automatically

### Slack Integration
Get briefings and notifications in Slack.

1. Create a Slack App at api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `channels:read`
3. Install to workspace
4. Copy Bot User OAuth Token
5. Add to `.env`: `SLACK_BOT_TOKEN=xoxb-...` and `SLACK_CHANNEL_ID=C...`

### Gamma API (Slide Generation)
Generate presentations from markdown.

1. Get an API key from gamma.app
2. Add to `.env`: `GAMMA_API_KEY=your-key`

## Tier 3: Power User Upgrades

### Vector Memory (mem0 + Pinecone)
The ultimate memory upgrade. See `docs/MEMORY-UPGRADE.md` for full setup.

- Automatic fact extraction from every conversation
- Semantic search across all memories
- Cloud-stored, portable, ~$0.04/month

### Telegram Bot (Mobile AI OS Access)
Access your AI OS from your phone. The bot polls for messages, invokes Claude Code, and responds with full memory integration.

**Prerequisite:** Memory system must be installed first (run `python3 setup_memory.py`).

**Setup:**

1. Create a bot via @BotFather on Telegram
2. Copy the bot token
3. Add to `.env`: `TELEGRAM_BOT_TOKEN=your-token`
4. Add to `.env`: `ANTHROPIC_API_KEY=your-anthropic-key`
5. Find your Telegram user ID: message `@userinfobot` on Telegram
6. Edit `.claude/skills/telegram/references/messaging.yaml`:
   ```yaml
   allowed_user_ids: [YOUR_USER_ID]
   ```
7. Test the bot:
   ```bash
   python3 .claude/skills/telegram/scripts/telegram_handler.py --check
   python3 .claude/skills/telegram/scripts/telegram_handler.py --test "Hello, what do you know about me?"
   ```
8. Start the daemon:
   ```bash
   python3 .claude/skills/telegram/scripts/telegram_handler.py
   ```

**Features:**
- Whitelist-based security (reject by default)
- Rate limiting (30/min, 200/hour)
- Blocked command patterns (rm -rf, sudo, DROP TABLE)
- Memory auto-load (searches Pinecone for relevant context per message)
- Memory auto-capture (feeds exchanges into mem0 for future recall)
- Streaming progress updates during long operations
- SQLite message history (`data/messages.db`)

### n8n Workflows
Event-driven automation with visual workflows.

1. Self-host n8n or use n8n.cloud
2. Create webhooks for triggers
3. Add n8n MCP server config
4. Build workflows that call Claude headless mode

### Firecrawl (Web Scraping)
Extract data from specific URLs (NOT for research — use Perplexity for that).

1. Get API key from firecrawl.dev
2. Add to `.env`: `FIRECRAWL_API_KEY=your-key`
3. Add MCP config (see docs/MCP-SERVERS.md)

## Upgrade Priority

If you're adding capabilities incrementally, this is the recommended order:

1. **Vector memory** (mem0) — Biggest single upgrade. Your OS gets smarter over time.
2. **Perplexity** — Research quality jumps significantly.
3. **Slack** — Get briefings without opening a terminal.
4. **Gmail API** — Automate the email-digest skill.
5. **Gamma** — Slide generation is nice-to-have.
6. **Telegram** — Mobile access for on-the-go queries.
7. **n8n** — Only if you need complex event-driven automation.
