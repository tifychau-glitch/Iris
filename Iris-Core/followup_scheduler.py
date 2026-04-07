"""
IRIS Core -- Follow-up scheduler for accountability funnel.

Sends timed follow-up messages after Mt. Everest completion:
  T+1 day:  Telegram check-in
  T+3 days: Telegram pattern observation
  T+5 days: Telegram personalized nudge + Pro tease
  T+7 days: Email recap + upgrade CTA

Run via cron every hour:
  0 * * * * cd /path/to/iris-core && python3 followup_scheduler.py
"""

import asyncio
import logging
import sys
import os
from email.header import Header

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(__file__))

import config
import database as db
from email_sender import send_mt_everest_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---- Follow-up message templates ----

def build_1d_message(summary: str) -> str:
    """T+1 day: Warm check-in."""
    goal = _extract_goal(summary)
    return (
        f"Day one.\n\n"
        f"You said your mountain is: {goal}\n\n"
        f"What did you actually do today to move toward it?"
    )


def build_3d_message(summary: str) -> str:
    """T+3 days: Pattern observation."""
    goal = _extract_goal(summary)
    return (
        f"Three days since you defined your mountain.\n\n"
        f"What's gotten in the way so far?"
    )


def build_5d_message(summary: str) -> str:
    """T+5 days: Personalized nudge referencing their ceiling + Pro tease."""
    ceiling = _extract_section(summary, "THE CEILING")
    goal = _extract_goal(summary)

    if ceiling:
        msg = (
            f"Five days in.\n\n"
            f"You told me your biggest ceiling was: {ceiling}\n\n"
            f"How's that going? Still the thing, or has something else surfaced?"
        )
    else:
        msg = (
            f"Five days in.\n\n"
            f"How's the momentum on {goal}?"
        )

    msg += (
        "\n\n---\n\n"
        "This is what I do in IRIS Pro. Every day. "
        "Adapted to how you're actually performing -- not a generic reminder.\n\n"
        f"{config.PRO_UPGRADE_URL}"
    )
    return msg


def build_7d_email_html(summary: str) -> str:
    """T+7 days: Email recap + upgrade CTA."""
    goal = _extract_goal(summary)
    ceiling = _extract_section(summary, "THE CEILING")
    why = _extract_section(summary, "WHY THIS GOAL")

    ceiling_html = f'<div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 24px;">Your biggest ceiling was: <span style="color: #ff6b4a;">{ceiling}</span></div>' if ceiling else ""
    why_html = f'<div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 24px;">Because what you really want is: <span style="color: #4a9eff;">{why}</span></div>' if why else ""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; background: #0a0a0a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
    <div style="max-width: 560px; margin: 0 auto; padding: 48px 32px;">
        <div style="font-size: 24px; font-weight: 600; color: #fff; margin-bottom: 8px;">
            One week since you defined your mountain.
        </div>
        <div style="font-size: 14px; color: #666; margin-bottom: 40px;">
            A check-in from IRIS
        </div>

        <div style="border-top: 1px solid #222; padding-top: 32px;">
            <div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 24px;">
                Seven days ago, you said your goal was:<br>
                <span style="color: #fff; font-weight: 500;">{goal}</span>
            </div>

            {ceiling_html}

            {why_html}

            <div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 32px;">
                So here's the real question: did the last seven days move the needle?
            </div>

            <div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 32px;">
                If you're honest and the answer is no -- that's not failure. That's data.
                The gap between what you said and what you did is just information.
            </div>

            <div style="font-size: 16px; color: #e0e0e0; line-height: 1.6; margin-bottom: 32px;">
                But information without a system is just awareness. And awareness alone
                doesn't close gaps.
            </div>
        </div>

        <div style="background: #141414; border: 1px solid #222; border-radius: 8px;
                    padding: 24px; margin-top: 16px;">
            <div style="font-size: 18px; font-weight: 600; color: #fff; margin-bottom: 12px;">
                What IRIS Pro does differently
            </div>
            <div style="font-size: 15px; color: #bbb; line-height: 1.6; margin-bottom: 8px;">
                Builds your calendar around your mountain. Not a generic planner --
                specific blocks tied to your milestones.
            </div>
            <div style="font-size: 15px; color: #bbb; line-height: 1.6; margin-bottom: 8px;">
                Checks in every day. Adjusts tone based on whether you're
                executing or avoiding.
            </div>
            <div style="font-size: 15px; color: #bbb; line-height: 1.6; margin-bottom: 16px;">
                Remembers everything. Patterns, excuses, wins. Uses it all to
                keep you honest.
            </div>
            <div style="text-align: center;">
                <a href="{config.PRO_UPGRADE_URL}"
                   style="display: inline-block; background: #fff; color: #000;
                          padding: 14px 32px; border-radius: 8px; text-decoration: none;
                          font-weight: 600; font-size: 16px;">
                    Get IRIS Pro
                </a>
            </div>
        </div>

        <div style="border-top: 1px solid #222; margin-top: 40px; padding-top: 24px;
                    font-size: 13px; color: #555; line-height: 1.5;">
            You're receiving this because you completed a Mt. Everest session with IRIS.
        </div>
    </div>
</body>
</html>"""


# ---- Helpers ----

def _extract_goal(summary: str) -> str:
    """Extract the goal line from summary."""
    for line in summary.split("\n"):
        if line.strip().upper().startswith("THE GOAL:"):
            return line.split(":", 1)[1].strip()
    return "your goal"


def _extract_section(summary: str, section: str) -> str:
    """Extract a section value from the summary."""
    for line in summary.split("\n"):
        if line.strip().upper().startswith(section.upper() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


# ---- Scheduler ----

async def send_telegram_message(telegram_id: int, text: str) -> bool:
    """Send a Telegram message to a user."""
    from telegram import Bot

    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("No Telegram bot token configured")
        return False

    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Follow-up Telegram sent to {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram to {telegram_id}: {e}")
        return False


def send_followup_email(email: str, summary: str) -> bool:
    """Send the 7-day recap email."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured -- skipping email")
        return False

    goal = _extract_goal(summary)
    subject = f"One week on your mountain"

    html_body = build_7d_email_html(summary)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = Header(config.FROM_EMAIL, 'utf-8')
    msg["To"] = Header(email, 'utf-8')

    plain = f"One week since you defined your Mt. Everest: {goal}\n\nDid the last seven days move the needle?\n\nGet IRIS Pro: {config.PRO_UPGRADE_URL}"
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.FROM_EMAIL, email, msg.as_string())
        logger.info(f"7-day follow-up email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send follow-up email to {email}: {e}")
        return False


async def run_followups():
    """Process all pending follow-ups."""
    # Run migration in case DB is from before follow-up columns existed
    db.migrate_followup_columns()

    followup_schedule = [
        (1, "followup_1d_sent", "telegram", build_1d_message),
        (3, "followup_3d_sent", "telegram", build_3d_message),
        (5, "followup_5d_sent", "telegram", build_5d_message),
        (7, "followup_7d_email_sent", "email", None),
    ]

    total_sent = 0

    for day_offset, column, channel, msg_builder in followup_schedule:
        pending = db.get_pending_followups(day_offset, column)

        for session in pending:
            telegram_id = session["telegram_id"]
            email = session["email"]
            summary = session["summary"] or ""

            if channel == "telegram" and msg_builder:
                message = msg_builder(summary)
                success = await send_telegram_message(telegram_id, message)
            elif channel == "email":
                success = send_followup_email(email, summary)
            else:
                continue

            if success:
                db.mark_followup_sent(telegram_id, column)
                total_sent += 1
                logger.info(
                    f"Sent {column} to user {telegram_id} ({channel})"
                )

    if total_sent:
        logger.info(f"Follow-up run complete: {total_sent} messages sent")
    else:
        logger.info("Follow-up run complete: no pending follow-ups")


def main():
    """Entry point for cron execution."""
    db.init_db()
    asyncio.run(run_followups())


if __name__ == "__main__":
    main()
