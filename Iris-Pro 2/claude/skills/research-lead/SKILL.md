---
name: research-lead
description: Transform a LinkedIn URL into a complete research package with personalized outreach. Scrapes profile, researches company via Perplexity, runs AI analysis for pain points and DM sequences, stores results in Google Sheets. Run with /research-lead or ask to research a lead.
model: sonnet
context: fork
allowed-tools: Bash(python3 .claude/skills/research-lead/scripts/*)
user-invocable: true
---

# Lead Research & Personalization

## Objective

Transform a LinkedIn URL into a complete research package with personalized outreach content — constrained to **relevant personalization only**.

Relevant = relates to a problem they're likely facing that we can solve.
Theater = personal but irrelevant (marathons, shared schools, hobbies).

Before including any fact, apply this test: "Does this relate to a problem they're facing that we can solve?" If no, discard it.

## Inputs Required

- LinkedIn URL (e.g., `https://www.linkedin.com/in/username/`)
- Google Sheets document ID (optional — where to store results)

## Quick Start

```bash
python3 .claude/skills/research-lead/scripts/research_lead.py "https://www.linkedin.com/in/username/"
```

Add `--post-to-slack` to post the review card to Slack.

## Execution Steps

### Step 1: Scrape LinkedIn Profile

```bash
python3 .claude/skills/research-lead/scripts/scrape_linkedin.py "LINKEDIN_URL"
```

**Output**: JSON — name, headline, company, role, experience, recent posts, skills
**Dependencies**: RELEVANCE_AI_API_KEY (for scraping API)

### Step 2: Research Company (Perplexity)

```bash
python3 .claude/skills/research-lead/scripts/research_with_perplexity.py --company "Company Name" --person "Person Name" --role "Their Role"
```

**Output**: JSON — company overview, recent news, industry, challenges, tech stack signals
**Dependencies**: PERPLEXITY_API_KEY

### Step 3: AI Analysis (Parallel — runs 5 analyses simultaneously)

```bash
python3 .claude/skills/research-lead/scripts/analyze_with_openai.py --type lead_profile --profile profile.json --research research.json
python3 .claude/skills/research-lead/scripts/analyze_with_openai.py --type pain_gain_operational --profile profile.json --research research.json
python3 .claude/skills/research-lead/scripts/analyze_with_openai.py --type pain_gain_automation --profile profile.json --research research.json
python3 .claude/skills/research-lead/scripts/analyze_with_openai.py --type connection_request --profile profile.json --research research.json
python3 .claude/skills/research-lead/scripts/analyze_with_openai.py --type dm_sequence --profile profile.json --research research.json
```

**Analysis types:**
- `lead_profile` — Structured profile summary with relevance filter
- `pain_gain_operational` — Business pain points and potential gains
- `pain_gain_automation` — Automation-specific opportunities
- `connection_request` — Personalized LinkedIn connection message
- `dm_sequence` — 3-message DM sequence (value-first, not salesy)

**Dependencies**: OPENAI_API_KEY

### Step 4: Generate Review Report

```bash
python3 .claude/skills/research-lead/scripts/generate_review_report.py --data combined_analysis.json
```

**Output**: HTML report for human review before sending anything

### Step 5: Store in Google Sheets (Optional)

```bash
python3 .claude/skills/research-lead/scripts/update_google_sheet.py --data combined_analysis.json --sheet-id "SHEET_ID"
```

### Step 6: Post to Slack (Optional)

```bash
python3 .claude/skills/research-lead/scripts/post_lead_review_to_slack.py --data combined_analysis.json
```

## Process Flow

```
LinkedIn URL
   ↓
1. Scrape profile → profile.json
   ↓
2. Research company → research.json
   ↓
3. AI analysis (5x parallel) → analyses.json
   ↓
4. Generate review report → report.html
   ↓
5. (Optional) Store → Google Sheets
   ↓
6. (Optional) Post → Slack for review
```

## Batch Processing

```bash
python3 .claude/skills/research-lead/scripts/batch_research_leads.py --source airtable
```

Pulls unprocessed leads from Airtable, runs the full pipeline for each.

## Edge Cases

- **Profile is private**: Report what's available, note limitations
- **Company not found**: Research using available signals (headline, posts)
- **Rate limits**: Built-in retry with exponential backoff in each script
- **Missing API keys**: Scripts fail gracefully with clear error message about which key is missing

## Environment Variables Required

```bash
RELEVANCE_AI_API_KEY=     # LinkedIn scraping
PERPLEXITY_API_KEY=       # Company research
OPENAI_API_KEY=           # AI analysis
SLACK_BOT_TOKEN=          # Optional: Slack posting
GOOGLE_SHEETS_CREDENTIALS= # Optional: Google Sheets storage
```

## Cost

~$0.40 per lead (API calls combined). Pipeline takes 45-60 seconds.
