#!/usr/bin/env python3
"""
IRIS Core -- Test Email Sending
Tests Mt. Everest email delivery with calendar attachments.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import print_header, print_section, print_success, print_error, print_info
import config
from email_sender import send_mt_everest_email
from calendar_generator import generate_calendar_png, generate_ics


def test_email_sending():
    """Test email sending functionality."""

    print_header("IRIS CORE - EMAIL SENDING TEST")

    # Sample summary
    summary = """
THE GOAL:
Build a SaaS business that achieves $1M ARR within 3 years.

WHY THIS GOAL:
Financial independence and the ability to create tools that help others.

THE CEILING:
Fear of running out of money before reaching profitability.

IDENTITY SHIFTS:
Becoming a founder who can sell and market, not just a developer.

MILESTONES:
- 12-Month: $100K ARR with product people pay for
- 90-Day: MVP launched with 10 paying customers
- This Month: Validate customer problem, start MVP
"""

    test_email = "tiffanychau@gmail.com"

    print_section("Email Configuration Check")
    if config.SMTP_USER and config.SMTP_PASSWORD:
        print_success(f"SMTP configured with user: {config.SMTP_USER}")
    else:
        print_error("SMTP credentials not configured in .env")
        print_info("To enable email testing, add to .env:")
        print("  SMTP_USER=your-gmail@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
        print("  FROM_EMAIL=your-email@gmail.com")
        print("\n(Get app password from: https://myaccount.google.com/apppasswords)")
        return False

    print_section("Generating Calendar Attachments")
    try:
        calendar_png = generate_calendar_png(summary)
        calendar_ics = generate_ics(summary)
        print_success(f"Calendar PNG ready ({len(calendar_png)} bytes)")
        print_success(f"ICS file ready ({len(calendar_ics)} bytes)")
    except Exception as e:
        print_error(f"Failed to generate calendar: {e}")
        return False

    print_section("Sending Email")
    print_info(f"To: {test_email}")
    print_info(f"From: {config.FROM_EMAIL}")

    try:
        result = send_mt_everest_email(
            to_email=test_email,
            summary=summary,
            calendar_png=calendar_png,
            calendar_ics=calendar_ics
        )

        if result:
            print_success("Email sent successfully!")
            print_info(f"Subject: Your Mt. Everest -- Build a SaaS business...")
            print_info(f"Attachments: Calendar PNG (inline), ICS file (attachment)")
        else:
            print_error("Email sending failed (check SMTP credentials)")
            return False

    except Exception as e:
        print_error(f"Exception during email send: {e}")
        return False

    print_header("✓ EMAIL SENDING TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_email_sending()
    sys.exit(0 if success else 1)
