from __future__ import annotations

"""
IRIS Core -- Telegram bot + web signup form.
Single process serving both the Telegram bot and a Flask signup page.
"""

import asyncio
import logging
import re
import secrets
import threading
from datetime import datetime, timedelta

import anthropic
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import config
import database as db
from iris_prompt import (
    format_new_session_prompt,
    format_message_prompt,
    format_checkin_message,
)
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Anthropic client
claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

# In-memory conversation history (per user, kept small for token efficiency)
# Structure: {telegram_id: [{"role": "user"/"assistant", "content": "..."}]}
conversations: dict[int, list[dict]] = {}

# ---- Telegram Handlers ----


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start -- check whitelist or claim signup token."""
    user_id = update.effective_user.id
    args = context.args

    # Check if this is a deeplink with signup token
    if args and args[0].startswith("signup_"):
        token = args[0]
        email = db.claim_signup(token, user_id)
        if email:
            logger.info(f"User {user_id} claimed signup for {email}")
            await update.message.reply_text(
                "Hey. I'm IRIS.\n\n"
                "I track what you say you'll do -- and whether you actually do it.\n\n"
                "What's something you've been putting off?"
            )
            # Start a new session
            db.create_session(user_id, "accountability")
            conversations[user_id] = []
            return
        else:
            await update.message.reply_text(
                "That signup link doesn't look right. "
                "Head to the signup page and try again."
            )
            return

    # Check if already registered
    if db.is_whitelisted(user_id):
        await update.message.reply_text(
            "Still here.\n\nWhat are you working on?"
        )
        # Start fresh session
        session = db.get_active_session(user_id)
        if session:
            db.close_session(session["id"])
        db.create_session(user_id, "accountability")
        conversations[user_id] = []
        return

    # Not registered
    await update.message.reply_text(
        "You need to sign up first before we can talk.\n\n"
        "Head to the signup page to get started."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check whitelist
    if not db.is_whitelisted(user_id):
        await update.message.reply_text(
            "Sign up first. Then we talk."
        )
        return

    # Check rate limit
    if not db.check_rate_limit(user_id, config.DAILY_MESSAGE_LIMIT):
        await update.message.reply_text(
            "That's enough for today. Talk tomorrow."
        )
        return

    db.increment_message_count(user_id)

    # Get or create session
    session = db.get_active_session(user_id)
    if not session:
        session_id = db.create_session(user_id, "accountability")
        session = db.get_active_session(user_id)
        conversations[user_id] = []

    session_id = session["id"]
    exchange_count = session["exchange_count"]
    session_type = session["session_type"]
    max_exchanges = (
        config.MAX_CHECKIN_EXCHANGES
        if session_type == "checkin"
        else config.MAX_EXCHANGES_PER_SESSION
    )

    # Check if session is at limit
    if exchange_count >= max_exchanges:
        db.close_session(session_id)
        # Start a new session
        session_id = db.create_session(user_id, "accountability")
        conversations[user_id] = []
        exchange_count = 0
        session_type = "accountability"

    # Build conversation history
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": text})

    # Keep history short (last 8 messages max for token efficiency)
    if len(conversations[user_id]) > 8:
        conversations[user_id] = conversations[user_id][-8:]

    # Get active commitments for context
    active_commitments = db.get_active_commitments(user_id)

    # Build prompt
    prompt_data = format_message_prompt(
        conversation_history=conversations[user_id],
        active_commitments=active_commitments,
        session_type=session_type,
        exchange_count=exchange_count,
        max_exchanges=max_exchanges,
    )

    # Call Anthropic API
    try:
        response = claude.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=300,  # Keep responses short
            system=prompt_data["system"],
            messages=prompt_data["messages"],
        )
        reply = response.content[0].text.strip()
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        reply = "Something went wrong on my end. Try again in a minute."

    # Store assistant response in history
    conversations[user_id].append({"role": "assistant", "content": reply})

    # Increment exchange count
    new_count = db.increment_exchange(session_id)

    # Try to extract commitment from the conversation
    await _try_extract_commitment(user_id, text, reply)

    # Auto-close if at limit after this exchange
    if new_count >= max_exchanges:
        db.close_session(session_id)

    await update.message.reply_text(reply)


async def _try_extract_commitment(user_id: int, user_text: str, iris_reply: str):
    """
    Heuristic: if IRIS's reply contains "I'll check in" or similar,
    try to extract the commitment and schedule a check-in.
    """
    reply_lower = iris_reply.lower()

    # Skip if no check-in language at all
    if not any(phrase in reply_lower for phrase in ["check in", "check back", "follow up", "hit you up"]):
        return

    # Try relative time first: "in 30 minutes", "in 2 hours", "in an hour"
    relative_patterns = [
        r"(?:check(?:\s*(?:in|back))?|follow up|hit you up)\s+(?:in\s+)?(\d+)\s*(min(?:ute)?s?|hours?|hrs?)",
        r"in\s+(\d+)\s*(min(?:ute)?s?|hours?|hrs?)",
        r"(?:check(?:\s*(?:in|back))?|follow up)\s+in\s+an?\s+(hour)",
    ]

    for pattern in relative_patterns:
        match = re.search(pattern, reply_lower)
        if match:
            groups = match.groups()
            # Handle "in an hour" case
            if groups[-1] == "hour" and len(groups) == 1:
                minutes = 60
            else:
                amount = int(groups[0])
                unit = groups[1]
                if unit.startswith("h"):
                    minutes = amount * 60
                else:
                    minutes = amount

            check_in_time = datetime.now() + timedelta(minutes=minutes)
            task = user_text[:200]
            db.add_commitment(user_id, task, check_in_time)
            logger.info(
                f"Commitment stored for user {user_id}: "
                f"'{task}' -- check-in in {minutes}min at {check_in_time.strftime('%H:%M')}"
            )
            return

    # Try absolute time: "at 3pm", "at 3:30 PM"
    absolute_patterns = [
        r"(?:check(?:\s*(?:in|back))?|follow up|hit you up)\s+(?:at|around|by)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
    ]

    for pattern in absolute_patterns:
        match = re.search(pattern, reply_lower)
        if match:
            time_str = match.group(1).strip()
            check_in_time = _parse_time(time_str)
            if check_in_time:
                task = user_text[:200]
                db.add_commitment(user_id, task, check_in_time)
                logger.info(
                    f"Commitment stored for user {user_id}: "
                    f"'{task}' at {check_in_time.strftime('%H:%M')}"
                )
                return


def _parse_time(time_str: str) -> datetime | None:
    """Parse a time string like '3pm', '3:30 PM' into today's or tomorrow's datetime."""
    now = datetime.now()

    time_str_clean = time_str.replace(" ", "").upper()

    for fmt in ["%I%p", "%I:%M%p"]:
        try:
            parsed_time = datetime.strptime(time_str_clean, fmt).time()
            result = now.replace(
                hour=parsed_time.hour,
                minute=parsed_time.minute,
                second=0,
                microsecond=0,
            )
            # If the time already passed today, schedule for tomorrow
            if result <= now:
                result += timedelta(days=1)
            return result
        except ValueError:
            continue

    return None


# ---- Flask Web Signup Form ----

app = Flask(__name__)

SIGNUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IRIS - Sign Up</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            max-width: 420px;
            width: 90%;
            padding: 48px 32px;
        }
        h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #fff;
        }
        .subtitle {
            font-size: 16px;
            color: #888;
            margin-bottom: 40px;
            line-height: 1.5;
        }
        form { display: flex; flex-direction: column; gap: 16px; }
        input[type="email"] {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 14px 16px;
            font-size: 16px;
            color: #fff;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="email"]:focus { border-color: #666; }
        input[type="email"]::placeholder { color: #555; }
        button {
            background: #fff;
            color: #000;
            border: none;
            border-radius: 8px;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        button:hover { opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .success {
            text-align: center;
            display: none;
        }
        .success h2 {
            font-size: 22px;
            margin-bottom: 16px;
            color: #fff;
        }
        .success p {
            color: #888;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .success a {
            display: inline-block;
            background: #fff;
            color: #000;
            padding: 14px 32px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 16px;
        }
        .success a:hover { opacity: 0.9; }
        .error { color: #e55; font-size: 14px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div id="form-section">
            <h1>Meet IRIS.</h1>
            <p class="subtitle">
                She tracks what you say you'll do -- and whether you actually do it.
                Free on Telegram.
            </p>
            <form id="signup-form">
                <input type="email" name="email" placeholder="Your email" required>
                <button type="submit">Get Started</button>
                <p class="error" id="error-msg"></p>
            </form>
        </div>
        <div class="success" id="success-section">
            <h2>You're in.</h2>
            <p>Open Telegram and message IRIS to get started.</p>
            <a id="telegram-link" href="#">Open Telegram</a>
        </div>
    </div>
    <script>
        document.getElementById('signup-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const errorEl = document.getElementById('error-msg');
            btn.disabled = true;
            errorEl.style.display = 'none';

            const email = e.target.email.value;
            try {
                const res = await fetch('/api/signup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email})
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('form-section').style.display = 'none';
                    document.getElementById('success-section').style.display = 'block';
                    document.getElementById('telegram-link').href = data.telegram_link;
                } else {
                    errorEl.textContent = data.error || 'Something went wrong.';
                    errorEl.style.display = 'block';
                    btn.disabled = false;
                }
            } catch {
                errorEl.textContent = 'Connection error. Try again.';
                errorEl.style.display = 'block';
                btn.disabled = false;
            }
        });
    </script>
</body>
</html>"""


@app.route("/")
def signup_page():
    return render_template_string(SIGNUP_HTML)


@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json()
    email = data.get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Valid email required."})

    # Generate signup token
    token = f"signup_{secrets.token_urlsafe(16)}"
    db.add_pending_signup(email, token)

    telegram_link = f"https://t.me/{config.BOT_USERNAME}?start={token}"

    logger.info(f"Signup: {email} -> token {token}")
    return jsonify({"success": True, "telegram_link": telegram_link})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "iris-core"})


# ---- Main ----


def run_flask():
    """Run Flask in a separate thread."""
    app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False)


async def send_checkin_message(bot: Bot, telegram_id: int, task: str, commit_id: int):
    """Send a proactive check-in message via Telegram."""
    message = format_checkin_message(task)
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
        logger.info(f"Check-in sent to {telegram_id}: {message}")

        # Create a check-in session for this user
        session = db.get_active_session(telegram_id)
        if session:
            db.close_session(session["id"])
        db.create_session(telegram_id, "checkin")

        # Pre-populate conversation with the check-in
        conversations[telegram_id] = [
            {"role": "assistant", "content": message}
        ]
    except Exception as e:
        logger.error(f"Failed to send check-in to {telegram_id}: {e}")


def main():
    """Start the bot, scheduler, and web server."""
    # Validate config
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    # Initialize database
    db.init_db()
    logger.info("Database initialized")

    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Web signup form running on port {config.WEB_PORT}")

    # Build Telegram application
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Start the check-in scheduler
    bot = application.bot
    start_scheduler(bot, send_checkin_message)
    logger.info("Check-in scheduler started")

    # Run the bot
    logger.info("IRIS Core bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
