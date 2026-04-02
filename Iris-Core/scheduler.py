"""
IRIS Core -- Check-in scheduler.
Uses APScheduler to poll for due commitments and send proactive Telegram messages.
"""

import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

import config
import database as db

logger = logging.getLogger(__name__)

# Reference to the send function (injected from bot.py)
_send_checkin = None
_bot = None


def _check_due_commitments():
    """Poll database for due check-ins and send messages."""
    # First, mark stale commitments as missed
    db.mark_stale_commitments(hours=config.MISSED_CHECKIN_HOURS)

    # Get all due check-ins
    due = db.get_due_checkins()
    if not due:
        return

    logger.info(f"Found {len(due)} due check-ins")

    for commitment in due:
        telegram_id = commitment["telegram_id"]
        task = commitment["task"]
        commit_id = commitment["id"]

        # Mark as checked (so we don't send again)
        db.update_commitment_status(commit_id, "checking_in")

        # Send the check-in message via the bot
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                _send_checkin(_bot, telegram_id, task, commit_id)
            )
            loop.close()
        except Exception as e:
            logger.error(f"Failed to send check-in for commitment {commit_id}: {e}")
            # Revert status so it gets retried
            db.update_commitment_status(commit_id, "pending")


def start_scheduler(bot: Bot, send_checkin_fn):
    """
    Start the background scheduler.

    Args:
        bot: Telegram Bot instance for sending messages
        send_checkin_fn: Async function(bot, telegram_id, task, commit_id)
                         that sends the check-in message
    """
    global _send_checkin, _bot
    _send_checkin = send_checkin_fn
    _bot = bot

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _check_due_commitments,
        "interval",
        seconds=config.CHECKIN_POLL_INTERVAL_SECONDS,
        id="checkin_poll",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler running -- polling every "
        f"{config.CHECKIN_POLL_INTERVAL_SECONDS}s for due check-ins"
    )
    return scheduler
