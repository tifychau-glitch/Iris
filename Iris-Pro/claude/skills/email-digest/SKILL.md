---
name: email-digest
description: Process Gmail inbox to identify high-risk emails, analyze sentiment and urgency, generate strategic recommendations, create draft responses, and deliver an executive briefing to Slack. Run with /email-digest or ask to process emails.
model: sonnet
context: fork
allowed-tools: Bash(python3 .claude/skills/email-digest/scripts/*)
user-invocable: true
---

# Email Digest

Automated inbox processing: fetch → analyze → brief → respond.

## Objective

Process the Gmail inbox to identify high-risk/high-priority emails, analyze sentiment and urgency, generate strategic recommendations, optionally create draft responses, and deliver an executive briefing.

## Inputs Required

- Gmail API credentials (see `docs/UPGRADE-PATHS.md` for setup)
- Slack webhook or bot token (optional — for Slack delivery)

## Execution Steps

### Step 1: Fetch Emails

```bash
python3 .claude/skills/email-digest/scripts/fetch_emails.py --hours 24
```

**Output**: JSON array of emails with: sender, subject, body, timestamp, thread_id, labels
**Options**: `--hours 24` (default), `--unread-only`, `--label INBOX`

### Step 2: Analyze Emails

```bash
python3 .claude/skills/email-digest/scripts/analyze_emails.py --input emails.json
```

**For each email, produces:**
- **Category**: urgent / respond / delegate / archive / irate
- **Sentiment**: positive / neutral / negative / irate
- **Urgency**: high / medium / low
- **Summary**: 1-sentence summary
- **Recommendation**: What to do and why
- **Draft response**: Suggested reply (if category is urgent or respond)

**Special detection — IRATE CLIENT:**
If sentiment analysis detects anger, frustration, or escalation:
- Flag as highest priority
- Generate immediate de-escalation response
- Recommend same-day personal follow-up
- Note in daily log

### Step 3: Post Executive Briefing to Slack

```bash
python3 .claude/skills/email-digest/scripts/post_to_slack_blocks.py --input analysis.json
```

**Briefing format:**
```
📊 Email Digest — [Date]
━━━━━━━━━━━━━━━━━━━━━━━

🔴 URGENT (2)
• [Sender] — [Subject] — [Recommendation]
• [Sender] — [Subject] — [Recommendation]

🟡 RESPOND (5)
• [Sender] — [Subject] — [Summary]
...

🟢 LOW PRIORITY (12)
• [count] emails archived
• [count] newsletters skipped
```

### Step 4: Create Draft Responses (Optional)

```bash
python3 .claude/skills/email-digest/scripts/create_gmail_drafts.py --input analysis.json
```

Creates Gmail drafts for urgent and respond-category emails. Reads `context/my-voice.md` for tone.

## Process Flow

```
Gmail Inbox
   ↓
1. Fetch (last 24h) → emails.json
   ↓
2. Analyze (sentiment + urgency + recommendations) → analysis.json
   ↓
3. Post briefing → Slack
   ↓
4. (Optional) Create drafts → Gmail
```

## Automation

Schedule with headless mode:

```bash
# Daily at 7am
0 7 * * * claude -p "/email-digest" --output-format json >> logs/email-digest.log
```

## Edge Cases

- **No urgent emails**: Still post briefing with summary stats
- **Gmail API rate limit**: Built-in retry with exponential backoff
- **Very long threads**: Summarize thread, don't analyze each message separately
- **Missing credentials**: Fail gracefully, suggest manual email-assistant skill instead

## Environment Variables Required

```bash
GOOGLE_CLIENT_ID=         # Gmail API
GOOGLE_CLIENT_SECRET=     # Gmail API
SLACK_BOT_TOKEN=          # Slack posting
SLACK_CHANNEL_ID=         # Where to post briefings
OPENAI_API_KEY=           # Sentiment analysis
```
