# IRIS Core

Free Mt. Everest goal-definition session on Telegram. One deep conversation to define your 3-5 year north star.

## What It Does

- Users sign up via web form (email capture)
- Message IRIS on Telegram for a single deep excavation session
- IRIS helps them define their Mt. Everest -- specific goal, real why, biggest obstacle, identity shifts, milestones
- Summary emailed to the user at the end
- Post-session: upgrade path to IRIS Pro for ongoing accountability

## Architecture

- Python Telegram bot (python-telegram-bot)
- Anthropic Claude API for conversation
- SQLite for user data and session tracking
- Flask for the signup web form
- Gmail SMTP for summary delivery
- Single process, single deploy

## Local Development

```bash
cd iris-core
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys

python3 bot.py
```

## Deploy to Hostinger VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

sudo mkdir -p /opt/iris-core
sudo chown $USER:$USER /opt/iris-core

# Upload files (from local machine)
scp -r ./* user@your-vps-ip:/opt/iris-core/

# On the VPS:
cd /opt/iris-core
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env  # Add your API keys

mkdir -p data

sudo cp iris-core.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable iris-core
sudo systemctl start iris-core

# Check status
sudo systemctl status iris-core
sudo journalctl -u iris-core -f
```

## Token Cost Estimate

Using Claude Sonnet with uncapped output per response:
- ~$0.15-0.25 per user (one-time, 8-15 exchange session)
- At 100 signups: ~$15-25 total (not recurring)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ANTHROPIC_API_KEY | Yes | - | Anthropic API key |
| TELEGRAM_BOT_TOKEN | Yes | - | Telegram bot token from BotFather |
| ANTHROPIC_MODEL | No | claude-sonnet-4-20250514 | Model to use |
| BOT_USERNAME | No | IrisAccountabilityBot | Bot username (without @) |
| WEB_PORT | No | 8080 | Signup form port |
| PRO_UPGRADE_URL | No | https://iris-ai.co | Pro upgrade link |
| SMTP_USER | No | - | Gmail address for sending summaries |
| SMTP_PASSWORD | No | - | Gmail app password |
| FROM_EMAIL | No | SMTP_USER | Sender address |
