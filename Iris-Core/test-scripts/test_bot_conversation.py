#!/usr/bin/env python3
"""
IRIS Core -- Test Bot Conversation
Simulates a full Mt. Everest excavation conversation with IRIS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import (
    print_header, print_section, print_success, print_error, print_info,
    reset_test_db, create_test_user, create_test_session,
    save_test_message, save_test_summary, get_test_session
)
import config
from iris_prompt import format_opening_prompt, format_message_prompt, get_upgrade_message
from bot import invoke_claude

# Test user ID
TEST_USER = 123456789


def simulate_conversation():
    """Simulate a full Mt. Everest conversation."""

    print_header("IRIS CORE - BOT CONVERSATION TEST")

    # Setup
    print_section("Setup")
    reset_test_db()
    create_test_user(TEST_USER, "test@example.com")
    create_test_session(TEST_USER)
    print_success("Test database and user created")

    # Get opening message
    print_section("Opening Message")
    try:
        opening = invoke_claude(format_opening_prompt(), messages=[], timeout=60)
        print_info("IRIS (opening):")
        print(f"\n{opening}\n")
        save_test_message(TEST_USER, "assistant", opening)
    except Exception as e:
        print_error(f"Failed to get opening: {e}")
        return False

    # Simulate user inputs
    user_inputs = [
        "I want to build a successful SaaS business that does $1M ARR in the next 3 years.",
        "Because I want financial independence and the ability to help others with the tools I build.",
        "Honestly, I'm scared I'll run out of money before we get to profitability.",
        "I need to become someone who can sell and market, not just code.",
        "12 months: $100K ARR and a product people actually want to pay for.",
    ]

    print_section("Conversation Exchanges")
    conversation = [{"role": "assistant", "content": opening}]

    for i, user_input in enumerate(user_inputs, 1):
        print_info(f"User (exchange {i}):")
        print(f"{user_input}\n")

        # Add user message to conversation
        conversation.append({"role": "user", "content": user_input})
        save_test_message(TEST_USER, "user", user_input)

        # Get IRIS response
        try:
            prompt = format_message_prompt(conversation, exchange_count=i)
            response = invoke_claude(prompt["system"], prompt["messages"], timeout=60)

            print_info("IRIS (response):")
            print(f"{response}\n")

            conversation.append({"role": "assistant", "content": response})
            save_test_message(TEST_USER, "assistant", response)

        except Exception as e:
            print_error(f"Failed at exchange {i}: {e}")
            return False

    # Simulate summary generation
    print_section("Summary Generation")
    summary = f"""
THE GOAL:
Build a SaaS business that achieves $1M ARR within 3 years.

WHY THIS GOAL:
Financial independence and the ability to create tools that help others.

THE CEILING:
Fear of running out of money before reaching profitability. Need to master sales and marketing beyond just coding.

IDENTITY SHIFTS:
Becoming a founder who can sell and market, not just a developer.

MILESTONES:
- 12-Month: $100K ARR with a product people pay for
- 90-Day: MVP launched and first 10 paying customers
- This Month: Validate problem with target customers and start building MVP
"""

    print_info("Generated Summary:")
    print(f"{summary}\n")

    save_test_summary(TEST_USER, summary)

    # Simulate upgrade prompt
    print_section("Upgrade Prompt")
    upgrade_url = config.PRO_UPGRADE_URL
    upgrade_msg = get_upgrade_message(upgrade_url)
    print_info("IRIS (upgrade):")
    print(f"{upgrade_msg}\n")

    # Save to session
    session = get_test_session(TEST_USER)
    print_section("Session State")
    print_info(f"Status: {session['status']}")
    print_info(f"Exchanges: {len(user_inputs)}")
    print_info(f"Summary saved: {'Yes' if session['summary'] else 'No'}")

    print_header("✓ CONVERSATION TEST PASSED")
    return True


if __name__ == "__main__":
    success = simulate_conversation()
    sys.exit(0 if success else 1)
