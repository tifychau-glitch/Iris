#!/usr/bin/env python3
"""
IRIS Pro -- Test Onboarding Flow
Tests user setup, business configuration, and initial account creation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import (
    print_header, print_section, print_success, print_error, print_info,
    reset_test_databases, create_test_user, get_accountability_db
)


def test_onboarding():
    """Test complete onboarding flow."""

    print_header("IRIS PRO - ONBOARDING TEST")

    # Step 1: Initialize test environment
    print_section("Step 1: Initialize Test Environment")
    try:
        reset_test_databases()
        print_success("Test databases initialized")
    except Exception as e:
        print_error(f"Failed to initialize databases: {e}")
        return False

    # Step 2: Create test user
    print_section("Step 2: Create User Account")
    test_user_id = "test-iris-user-001"
    test_email = "tiffanychau@gmail.com"

    try:
        user_id = create_test_user(test_user_id, test_email)
        print_success(f"User created: {user_id}")
        print_info(f"Email: {test_email}")
    except Exception as e:
        print_error(f"Failed to create user: {e}")
        return False

    # Step 3: Verify user in database
    print_section("Step 3: Verify User Account")
    try:
        conn = get_accountability_db()
        cursor = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (test_user_id,)
        )
        user_row = cursor.fetchone()
        conn.close()

        if user_row:
            user = dict(user_row)
            print_success("User verified in database")
            print_info(f"User ID: {user['user_id']}")
            print_info(f"Email: {user['email']}")
            print_info(f"Status: {user['status']}")
            print_info(f"Created: {user['created_at']}")
        else:
            print_error("User not found in database")
            return False
    except Exception as e:
        print_error(f"Failed to verify user: {e}")
        return False

    # Step 4: Simulate business details entry
    print_section("Step 4: Business Configuration")
    business_details = {
        "business_name": "IRIS Pro Test Business",
        "industry": "SaaS",
        "target_revenue": "$100K ARR",
        "main_goal": "Scale accountability platform",
        "team_size": "1"
    }

    try:
        print_success("Business details captured")
        for key, value in business_details.items():
            print_info(f"{key}: {value}")
    except Exception as e:
        print_error(f"Failed to capture business details: {e}")
        return False

    # Step 5: Test initial commitment setup
    print_section("Step 5: Initial Commitments")
    sample_commitments = [
        "Define first 90-day milestone",
        "Set up accountability check-ins",
        "Configure calendar for controlled time"
    ]

    try:
        from test_setup import create_test_commitment

        for i, commitment in enumerate(sample_commitments, 1):
            create_test_commitment(test_user_id, commitment)
            print_success(f"Commitment {i}: {commitment}")

    except Exception as e:
        print_error(f"Failed to create commitments: {e}")
        return False

    # Step 6: Verify onboarding complete
    print_section("Step 6: Verify Onboarding Status")
    try:
        from test_setup import get_commitments

        commitments = get_commitments(test_user_id)
        print_success(f"Onboarding flow complete")
        print_info(f"User has {len(commitments)} initial commitments")

        if len(commitments) >= 3:
            print_success("All initial commitments created")
        else:
            print_error("Not all commitments were created")
            return False

    except Exception as e:
        print_error(f"Failed to verify onboarding: {e}")
        return False

    print_header("✓ ONBOARDING TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_onboarding()
    sys.exit(0 if success else 1)
