# MCP Servers

Model Context Protocol (MCP) servers extend Claude Code with external service access. The AI OS works without any MCP servers — they're optional upgrades.

## How MCP Works

MCP servers run alongside Claude Code and provide tools for accessing external services (Notion, Slack, YouTube, etc.). Claude discovers available MCP tools automatically.

## Recommended Servers

### Tier 1: Free, High Value

**Notion** — Notes, wiki, CRM, databases
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "NOTION_TOKEN": "your-token"
      }
    }
  }
}
```
Get your token: notion.so/my-integrations

**Filesystem** — Advanced file operations
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

### Tier 2: Paid API, Worth It

**Perplexity** — Deep research (better than WebSearch for synthesis)
```json
{
  "mcpServers": {
    "perplexity": {
      "command": "npx",
      "args": ["-y", "@anthropic/perplexity-mcp-server"],
      "env": {
        "PERPLEXITY_API_KEY": "your-key"
      }
    }
  }
}
```

**Firecrawl** — Web scraping (extract data from specific URLs)
```json
{
  "mcpServers": {
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "your-key"
      }
    }
  }
}
```

### Tier 3: Power User

**YouTube Analytics** — Channel stats, video performance, transcripts
**Slack** — Team messaging, channel management
**Linear/GitHub** — Issue tracking, code management
**n8n** — Workflow automation (webhooks, integrations)

## Setup

Add MCP server configs to `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": {
        "API_KEY": "your-key"
      }
    }
  }
}
```

## Token Budget Warning

Each MCP server adds ~15K tokens to Claude's context. 4 servers = 60K tokens overhead. Only add servers you actively use. Python scripts calling APIs directly are cheaper for frequent operations.

## When to Use MCP vs Python Scripts

| Use MCP When... | Use Python Scripts When... |
|-----------------|---------------------------|
| Claude needs to reason about what to query | The query is always the same |
| Interactive exploration of data | Batch processing |
| One-off operations | Frequent operations (cost matters) |
| Real-time tool access needed | Results can be cached/stored |
