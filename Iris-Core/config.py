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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Mt. Everest session
MT_EVEREST_SOFT_LIMIT = 12          # Exchange count where IRIS starts wrapping toward summary
MAX_CONVERSATION_HISTORY = 20       # Messages kept in memory (full session context)
DAILY_MESSAGE_LIMIT = 50            # Messages per user per day

# Database
DB_PATH = Path(__file__).parent / "data" / "iris_core.db"

# Web signup form
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))

# Telegram bot deeplink base
BOT_USERNAME = os.getenv("BOT_USERNAME", "IrisAccountabilityBot")

# Pro upgrade URL
PRO_UPGRADE_URL = os.getenv("PRO_UPGRADE_URL", "https://iris-ai.co")

# Email delivery (Gmail SMTP)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail app password
FROM_EMAIL = os.getenv("FROM_EMAIL", "") or SMTP_USER
