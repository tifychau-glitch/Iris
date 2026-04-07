from __future__ import annotations

"""
IRIS Core -- Telegram bot + web signup form.
Single-session Mt. Everest goal excavation. One deep conversation per user,
then upgrade path to IRIS Pro.
"""

import json
import logging
import os
import re
import secrets
import subprocess
import sys
import threading

from flask import Flask, request, jsonify, render_template_string
from telegram import Update
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
    format_opening_prompt,
    format_message_prompt,
    get_upgrade_message,
    get_remind_prefix,
)
from email_sender import send_mt_everest_email
from calendar_generator import generate_calendar_png, generate_ics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory conversation history (per user)
# Structure: {telegram_id: [{"role": "user"/"assistant", "content": "..."}]}
conversations: dict[int, list[dict]] = {}

# Keywords that trigger showing the saved summary
REMIND_KEYWORDS = ["mt everest", "my goal", "my mountain", "remind me", "what's my goal", "my north star"]


# ---- AI Provider (shared abstraction layer) ----

# Try to import the shared ai_provider
# Checks: ./lib/ (VPS layout) and ../Iris-Pro/lib/ (local dev layout)
_ai_provider = None
for _lib_candidate in [
    os.path.join(os.path.dirname(__file__), "lib"),           # ~/iris-core/lib/
    os.path.join(os.path.dirname(__file__), "..", "Iris-Pro", "lib"),  # local dev
]:
    if os.path.isdir(_lib_candidate) and _lib_candidate not in sys.path:
        sys.path.insert(0, _lib_candidate)
        try:
            from ai_provider import ai as _ai_provider
            logger.info(f"Using ai_provider from {_lib_candidate}")
            break
        except ImportError:
            sys.path.remove(_lib_candidate)
            continue


def invoke_claude(system_prompt: str, messages: list = None, timeout: int = 120) -> str:
    """Route AI reasoning through the shared AI provider or Claude Code CLI.

    Args:
        system_prompt: The system prompt to send.
        messages: Optional conversation history [{"role": "user"/"assistant", "content": "..."}].
        timeout: Max seconds to wait for response.

    Returns:
        The assistant's reply text.
    """
    # Build the user message from conversation history
    user_message = ""
    if messages:
        parts = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "IRIS"
            parts.append(f"{role}: {msg['content']}")
        user_message = "\n\n".join(parts)

    # Use shared provider if available
    if _ai_provider:
        try:
            result = _ai_provider.reason(system_prompt, user_message, timeout=timeout)
            if result.startswith("[AI error]"):
                logger.error(f"AI provider error: {result}")
                return "Something went wrong on my end. Try again in a minute."
            return result
        except Exception as e:
            logger.error(f"AI provider exception: {e}")
            return "Something went wrong on my end. Try again in a minute."

    # Fallback: direct CLI call
    prompt_parts = [system_prompt]
    if user_message:
        prompt_parts.append("--- Conversation History ---")
        prompt_parts.append(user_message)

    full_prompt = "\n\n".join(prompt_parts)

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI error (exit {result.returncode}): {result.stderr[:500]}")
            return "Something went wrong on my end. Try again in a minute."

        data = json.loads(result.stdout)
        return data.get("result", "Something went wrong on my end. Try again in a minute.").strip()

    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timed out after {timeout}s")
        return "That took too long. Try again."
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Claude CLI parse error: {e}")
        return "Something went wrong on my end. Try again in a minute."


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

            # Create Mt. Everest session
            db.create_session(user_id)
            conversations[user_id] = []

            # Generate opening message via Claude
            opening = _get_opening_message()
            conversations[user_id].append({"role": "assistant", "content": opening})
            db.save_message(user_id, "assistant", opening)

            await update.message.reply_text(opening)
            return
        else:
            await update.message.reply_text(
                "That signup link doesn't look right. "
                "Head to the signup page and try again."
            )
            return

    # Check if already registered
    if db.is_whitelisted(user_id):
        session = db.get_session(user_id)
        if session:
            status = session["status"]
            if status in ("completed", "upgrade_only"):
                await update.message.reply_text(
                    "We already defined your mountain.\n\n"
                    "Say \"my Mt. Everest\" to see it again."
                )
                return
            elif status == "excavating":
                # Restore conversation history if lost (e.g. after restart)
                if user_id not in conversations:
                    conversations[user_id] = db.load_conversation(
                        user_id, limit=config.MAX_CONVERSATION_HISTORY
                    )
                await update.message.reply_text(
                    "Still here.\n\nWhere were we?"
                )
                return

        # Has account but no session somehow -- create one
        db.create_session(user_id)
        conversations[user_id] = []
        opening = _get_opening_message()
        conversations[user_id].append({"role": "assistant", "content": opening})
        db.save_message(user_id, "assistant", opening)
        await update.message.reply_text(opening)
        return

    # Not registered
    await update.message.reply_text(
        "You need to sign up first before we can talk.\n\n"
        "Head to the signup page to get started."
    )


def _get_opening_message() -> str:
    """Generate the opening message for a new Mt. Everest session."""
    reply = invoke_claude(format_opening_prompt(), messages=[], timeout=60)

    # If the CLI failed, use a sensible fallback
    if "went wrong" in reply or "too long" in reply:
        return (
            "Let's figure out what mountain you're actually climbing.\n\n"
            "Tell me what you're working toward -- even if it's fuzzy right now."
        )
    return reply


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check whitelist
    if not db.is_whitelisted(user_id):
        await update.message.reply_text("Sign up first. Then we talk.")
        return

    # Check rate limit
    if not db.check_rate_limit(user_id, config.DAILY_MESSAGE_LIMIT):
        await update.message.reply_text("That's enough for today. Talk tomorrow.")
        return

    db.increment_message_count(user_id)

    # Get session status
    session = db.get_session(user_id)
    if not session:
        # Shouldn't happen, but handle it
        db.create_session(user_id)
        session = db.get_session(user_id)

    status = session["status"]

    # ---- UPGRADE ONLY MODE ----
    if status in ("completed", "upgrade_only"):
        # Check if they're asking for their summary
        text_lower = text.lower()
        if any(kw in text_lower for kw in REMIND_KEYWORDS):
            summary = db.get_summary(user_id)
            if summary:
                await update.message.reply_text(
                    get_remind_prefix() + summary
                )
                return
            else:
                await update.message.reply_text(
                    "I don't have your summary saved. Something went wrong on my end."
                )
                return

        # Upgrade nudge
        if status == "completed":
            db.mark_upgrade_only(user_id)

        await update.message.reply_text(
            get_upgrade_message(config.PRO_UPGRADE_URL)
        )
        return

    # ---- ACTIVE EXCAVATION ----

    # Build conversation history -- load from DB if not in memory
    if user_id not in conversations:
        conversations[user_id] = db.load_conversation(
            user_id, limit=config.MAX_CONVERSATION_HISTORY
        )

    conversations[user_id].append({"role": "user", "content": text})
    db.save_message(user_id, "user", text)

    # Keep history within limit
    if len(conversations[user_id]) > config.MAX_CONVERSATION_HISTORY:
        conversations[user_id] = conversations[user_id][-config.MAX_CONVERSATION_HISTORY:]

    exchange_count = session["exchange_count"]

    # Build prompt
    prompt_data = format_message_prompt(
        conversation_history=conversations[user_id],
        exchange_count=exchange_count,
        soft_limit=config.MT_EVEREST_SOFT_LIMIT,
    )

    # Invoke Claude Code CLI (subscription-based, no API key needed)
    reply = invoke_claude(
        system_prompt=prompt_data["system"],
        messages=prompt_data["messages"],
    )

    # Store assistant response in history
    conversations[user_id].append({"role": "assistant", "content": reply})
    db.save_message(user_id, "assistant", reply)

    # Increment exchange count
    db.increment_exchange(user_id)

    # Check if this response contains the summary
    if _contains_summary(reply):
        db.save_summary(user_id, _extract_summary(reply))
        logger.info(f"Mt. Everest summary saved for user {user_id}")

        # Send calendar PNG via Telegram
        try:
            calendar_png = generate_calendar_png(_extract_summary(reply))
            await update.message.reply_photo(
                photo=calendar_png,
                caption="Your 12-month roadmap. Check your email for the full package.",
            )
        except Exception as e:
            logger.error(f"Failed to send calendar photo to {user_id}: {e}")

        # Send email with calendar in background
        email = db.get_user_email(user_id)
        if email:
            summary_text = db.get_summary(user_id)
            if summary_text:
                threading.Thread(
                    target=_send_email_background,
                    args=(user_id, email, summary_text),
                    daemon=True,
                ).start()

    await update.message.reply_text(reply)


def _contains_summary(text: str) -> bool:
    """Check if the response contains a Mt. Everest summary."""
    markers = ["THE GOAL:", "WHY THIS GOAL:", "THE CEILING:"]
    found = sum(1 for m in markers if m in text.upper())
    return found >= 2


def _extract_summary(text: str) -> str:
    """Extract the summary portion from the response."""
    # Find where the summary starts (first section label)
    labels = ["THE GOAL:", "WHY THIS GOAL:", "WHO I NEED TO BECOME:",
              "THE HONEST GAP:", "THE CEILING:", "MILESTONES:"]

    earliest = len(text)
    for label in labels:
        # Case-insensitive search
        idx = text.upper().find(label)
        if idx != -1 and idx < earliest:
            earliest = idx

    if earliest < len(text):
        return text[earliest:].strip()

    return text.strip()


def _send_email_background(user_id: int, email: str, summary: str):
    """Send the Mt. Everest email with calendar deliverables in a background thread."""
    try:
        calendar_png = generate_calendar_png(summary)
        calendar_ics = generate_ics(summary)
    except Exception as e:
        logger.error(f"Calendar generation failed for user {user_id}: {e}")
        calendar_png = None
        calendar_ics = None

    success = send_mt_everest_email(
        email, summary,
        calendar_png=calendar_png,
        calendar_ics=calendar_ics,
    )
    if success:
        db.mark_email_sent(user_id)


# ---- Flask Web Signup Form ----

flask_app = Flask(__name__)

SIGNUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IRIS - Define Your Mt. Everest</title>
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
            margin-bottom: 12px;
            line-height: 1.5;
        }
        .description {
            font-size: 14px;
            color: #666;
            margin-bottom: 40px;
            line-height: 1.6;
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
            <h1>Define Your Mt. Everest.</h1>
            <p class="subtitle">
                Get clear on the one goal that actually matters.
            </p>
            <p class="description">
                One free session with IRIS. She'll help you excavate your 3-5 year
                north star -- the specific goal, what's really driving it, and what's
                standing in the way. You'll walk away with clarity, not fluff.
            </p>
            <form id="signup-form">
                <input type="email" name="email" placeholder="Your email" required>
                <button type="submit">Start My Session</button>
                <p class="error" id="error-msg"></p>
            </form>
        </div>
        <div class="success" id="success-section">
            <h2>You're in.</h2>
            <p>Open Telegram and message IRIS to start your session.</p>
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


@flask_app.route("/")
def signup_page():
    return render_template_string(SIGNUP_HTML)


@flask_app.route("/api/signup", methods=["POST"])
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


@flask_app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "iris-core"})


# ---- Core → Pro Bridge API ----

# Simple in-memory rate limiter: {email: [timestamp, ...]}
_bridge_rate_limit: dict[str, list] = {}


@flask_app.route("/api/bridge/<email>")
def api_bridge(email):
    """Return Mt. Everest summary for a given email (Core → Pro bridge)."""
    from datetime import datetime

    email = email.strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Valid email required."}), 400

    # Rate limit: max 5 requests per email per hour
    now = datetime.now()
    hits = _bridge_rate_limit.get(email, [])
    hits = [t for t in hits if (now - t).total_seconds() < 3600]
    if len(hits) >= 5:
        return jsonify({"error": "Rate limited. Try again later."}), 429
    hits.append(now)
    _bridge_rate_limit[email] = hits

    data = db.get_bridge_data(email)
    if not data:
        return jsonify({"error": "No Mt. Everest session found for this email."}), 404

    return jsonify({
        "success": True,
        "summary": data["summary"],
        "completed_at": data["completed_at"],
    })


@flask_app.route("/api/bridge/<email>/download")
def api_bridge_download(email):
    """Download Mt. Everest data as a JSON file."""
    from flask import Response

    email = email.strip().lower()
    data = db.get_bridge_data(email)
    if not data:
        return jsonify({"error": "No Mt. Everest session found."}), 404

    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=mt-everest-{email.split('@')[0]}.json"},
    )


# ---- Main ----


def run_flask():
    """Run Flask in a separate thread."""
    flask_app.run(host=config.WEB_HOST, port=config.WEB_PORT, debug=False)


def main():
    """Start the bot and web server."""
    # Validate config
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

    # Run the bot
    logger.info("IRIS Core bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
