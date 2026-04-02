# IRIS Core

Free accountability bot on Telegram. Tracks what you say you'll do and whether you actually do it.

## What It Does

- Users sign up via web form (email capture)
- Message IRIS on Telegram
- IRIS extracts commitments and deadlines from conversation
- Sends check-in messages at scheduled times
- Tracks completion rate

## Architecture

- Python Telegram bot (python-telegram-bot)
- Anthropic Claude API for conversation
- SQLite for user data and commitments
- APScheduler for proactive check-ins
- Flask for the signup web form
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

Using Claude Sonnet with max 300 output tokens per response:
- ~$0.003-0.005 per conversation session (4 exchanges)
- ~$0.001 per check-in (1-2 exchanges)
- At 100 daily active users: ~$15-20/month

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ANTHROPIC_API_KEY | Yes | - | Anthropic API key |
| TELEGRAM_BOT_TOKEN | Yes | - | Telegram bot token from BotFather |
| ANTHROPIC_MODEL | No | claude-sonnet-4-20250514 | Model to use |
| BOT_USERNAME | No | IrisAccountabilityBot | Bot username (without @) |
| WEB_PORT | No | 8080 | Signup form port |
| PRO_URL | No | https://iris-ai.co | Pro upsell link |
