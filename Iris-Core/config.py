"""
IRIS Core -- Configuration and constants.
Loads environment variables and defines operational limits.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file
load_dotenv(Path(__file__).parent / ".env", override=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Anthropic model
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Token optimization limits
MAX_EXCHANGES_PER_SESSION = 4      # Max back-and-forth per accountability session
MAX_CHECKIN_EXCHANGES = 2          # Max exchanges after a check-in message
DAILY_MESSAGE_LIMIT = 50           # Messages per user per day

# Check-in scheduler
CHECKIN_POLL_INTERVAL_SECONDS = 60  # How often to check for due check-ins
MISSED_CHECKIN_HOURS = 24           # Hours before marking a check-in as missed

# Database
DB_PATH = Path(__file__).parent / "data" / "iris_core.db"

# Web signup form
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))

# Telegram bot deeplink base
BOT_USERNAME = os.getenv("BOT_USERNAME", "IrisAccountabilityBot")

# Pro upsell URL
PRO_URL = os.getenv("PRO_URL", "https://iris-ai.co")
