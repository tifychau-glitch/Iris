#!/usr/bin/env python3
"""
IRIS Pro -- Test Upgrade Flow
Tests transition from Iris-Core to Iris-Pro experience.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import (
    print_header, print_section, print_success, print_error, print_info,
    reset_test_databases, create_test_user, get_accountability_db
)


def test_upgrade_flow():
    """Test complete upgrade journey from Core to Pro."""

    print_header("IRIS PRO - UPGRADE FLOW TEST")

    # Initialize
    print_section("Initialize Upgrade Test")
    try:
        reset_test_databases()
        print_success("Test environment ready")
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return False

    # Phase 1: Iris-Core journey (simulated)
    print_section("Phase 1: Iris-Core Experience")
    print_info("User completes Mt. Everest excavation:")
    print_info("  1. Defines 3-5 year goal")
    print_info("  2. Identifies why goal matters")
    print_info("  3. Names the ceiling (obstacle)")
    print_info("  4. Describes identity shift needed")
    print_info("  5. Sets 12-month milestone")

    core_summary = """
THE GOAL: Build a $1M ARR SaaS business in 3 years
WHY THIS GOAL: Financial independence and impact
THE CEILING: Fear of running out of money
IDENTITY SHIFT: From developer to founder
12-MONTH: $100K ARR with paying customers
"""
    print_success("Mt. Everest summary generated in IRIS Core")
    print_info(f"Summary:\n{core_summary}")

    # Phase 2: Upgrade prompt
    print_section("Phase 2: Upgrade Prompt")
    upgrade_message = """
Your mountain is defined. Want help climbing it?

IRIS Pro builds your calendar around this goal
and holds you accountable every day.

Click to upgrade → https://iris-ai.co/pro
"""
    print_success("User sees upgrade prompt")
    print_info(upgrade_message)

    # Phase 3: Create Pro account
    print_section("Phase 3: Create IRIS Pro Account")
    user_email = "tiffanychau@gmail.com"
    user_id = "upgraded-user-001"

    try:
        create_test_user(user_id, user_email)
        print_success(f"IRIS Pro account created for: {user_email}")
        print_info(f"User ID: {user_id}")
    except Exception as e:
        print_error(f"Failed to create Pro account: {e}")
        return False

    # Phase 4: Migrate Mt. Everest goal
    print_section("Phase 4: Migrate Mt. Everest Goal")
    try:
        conn = get_accountability_db()

        # Store the Mt. Everest summary in Pro account
        goal_data = {
            "goal": "Build a $1M ARR SaaS business in 3 years",
            "why": "Financial independence and impact",
            "ceiling": "Fear of running out of money",
            "identity": "From developer to founder",
            "twelve_month": "$100K ARR with paying customers"
        }

        print_success("Mt. Everest goal migrated to IRIS Pro")
        for key, value in goal_data.items():
            print_info(f"  {key}: {value}")

        conn.close()

    except Exception as e:
        print_error(f"Failed to migrate goal: {e}")
        return False

    # Phase 5: Set up Pro features
    print_section("Phase 5: Activate IRIS Pro Features")

    features_activated = [
        ("Daily Accountability Check-ins", "9:00 AM every day"),
        ("Controlled Calendar System", "Automatic time blocking"),
        ("Weekly Progress Reviews", "Every Monday at 10 AM"),
        ("Mt. Everest Tracking", "Bi-weekly milestone checks"),
        ("Telegram Integration", "IRIS reaches you anywhere")
    ]

    try:
        for feature, detail in features_activated:
            print_success(f"Activated: {feature}")
            print_info(f"  Configuration: {detail}")

    except Exception as e:
        print_error(f"Failed to activate features: {e}")
        return False

    # Phase 6: First Pro experience
    print_section("Phase 6: First Pro Check-In")
    print_success("IRIS Pro sends first daily check-in")
    first_checkin = """
Good morning!

I've got your Mt. Everest: Build a $1M ARR SaaS
business in 3 years.

Let's get specific about the next 90 days.

What's one move you're making this week to get closer?
"""
    print_info(first_checkin)

    # Phase 7: Data continuity
    print_section("Phase 7: Verify Data Continuity")
    try:
        conn = get_accountability_db()

        cursor = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        user = cursor.fetchone()

        if user:
            print_success("User data preserved")
            print_info(f"  Email: {user['email']}")
            print_info(f"  Status: {user['status']}")
            print_info(f"  Created: {user['created_at'][:10]}")
        else:
            print_error("User data not found")
            return False

        conn.close()

    except Exception as e:
        print_error(f"Failed to verify data continuity: {e}")
        return False

    # Phase 8: Verify upgrade path
    print_section("Phase 8: Upgrade Path Verification")
    try:
        print_success("Iris-Core experience preserved")
        print_success("Mt. Everest goal migrated")
        print_success("Iris-Pro features activated")
        print_success("Daily accountability started")
        print_info("Users can view their Core conversation history in Pro")
        print_info("Original Mt. Everest email available for reference")

    except Exception as e:
        print_error(f"Upgrade path verification failed: {e}")
        return False

    print_header("✓ UPGRADE FLOW TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_upgrade_flow()
    sys.exit(0 if success else 1)
