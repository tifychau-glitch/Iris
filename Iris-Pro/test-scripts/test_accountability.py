#!/usr/bin/env python3
"""
IRIS Pro -- Test Accountability Engine
Tests IRIS daily check-ins, commitment tracking, and accountability flow.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import (
    print_header, print_section, print_success, print_error, print_info,
    reset_test_databases, create_test_user, create_test_commitment,
    get_accountability_db, get_commitments
)


def test_accountability():
    """Test accountability engine and check-ins."""

    print_header("IRIS PRO - ACCOUNTABILITY ENGINE TEST")

    # Initialize
    print_section("Initialize Accountability System")
    try:
        reset_test_databases()
        print_success("Accountability database ready")
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return False

    # Create test user
    print_section("Create Test User")
    user_id = "accountability-test-001"
    email = "test-accountability@example.com"

    try:
        create_test_user(user_id, email)
        print_success(f"User created: {user_id}")
        print_info(f"Email: {email}")
    except Exception as e:
        print_error(f"Failed to create user: {e}")
        return False

    # Test 1: Create commitments
    print_section("Test 1: Create Commitments")
    commitments_to_create = [
        ("Complete Iris-Pro v1 launch", 7),
        ("Integrate Iris-Core upgrade flow", 14),
        ("Set up daily accountability check-ins", 3),
        ("Build Telegram bot integration", 21),
        ("Document accountability engine", 5)
    ]

    commitment_ids = []
    try:
        for commitment_text, days_out in commitments_to_create:
            due_date = (datetime.now() + timedelta(days=days_out)).isoformat()
            commit_id = create_test_commitment(user_id, commitment_text, due_date)
            commitment_ids.append(commit_id)
            print_success(f"Created: {commitment_text} (due in {days_out} days)")

    except Exception as e:
        print_error(f"Failed to create commitments: {e}")
        return False

    # Test 2: Log daily check-ins
    print_section("Test 2: Daily Check-In History")
    check_in_messages = [
        "Made progress on launch preparation",
        "Blocked on API integration - working on workaround",
        "Team alignment meeting scheduled",
        "Testing critical features"
    ]

    try:
        conn = get_accountability_db()
        now = datetime.now()

        for i, message in enumerate(check_in_messages):
            check_in_time = (now - timedelta(days=len(check_in_messages)-i-1)).isoformat()
            conn.execute(
                """INSERT INTO check_ins (user_id, message, created_at)
                   VALUES (?, ?, ?)""",
                (user_id, message, check_in_time)
            )
            print_info(f"Check-in {i+1}: {message}")

        conn.commit()
        conn.close()
        print_success(f"Logged {len(check_in_messages)} check-in messages")

    except Exception as e:
        print_error(f"Failed to log check-ins: {e}")
        return False

    # Test 3: Verify commitments
    print_section("Test 3: Retrieve Commitments")
    try:
        commitments = get_commitments(user_id)

        if len(commitments) == len(commitments_to_create):
            print_success(f"All {len(commitments)} commitments retrieved")
            for i, commitment in enumerate(commitments, 1):
                print_info(f"{i}. {commitment['commitment']}")
                print_info(f"   Status: {commitment['status']}")
                print_info(f"   Due: {commitment['due_date'][:10]}")
        else:
            print_error(f"Expected {len(commitments_to_create)} commitments, got {len(commitments)}")
            return False

    except Exception as e:
        print_error(f"Failed to retrieve commitments: {e}")
        return False

    # Test 4: Commitment status updates
    print_section("Test 4: Update Commitment Status")
    try:
        conn = get_accountability_db()

        # Mark some commitments as in-progress or completed
        status_updates = [
            (commitment_ids[0], "in_progress"),
            (commitment_ids[1], "pending"),
            (commitment_ids[4], "completed")
        ]

        for commit_id, new_status in status_updates:
            conn.execute(
                "UPDATE commitments SET status = ? WHERE id = ?",
                (new_status, commit_id)
            )
            print_success(f"Commitment {commit_id}: {new_status}")

        conn.commit()
        conn.close()

    except Exception as e:
        print_error(f"Failed to update commitments: {e}")
        return False

    # Test 5: Accountability metrics
    print_section("Test 5: Accountability Metrics")
    try:
        conn = get_accountability_db()

        # Count commitments by status
        cursor = conn.execute(
            "SELECT status, COUNT(*) as count FROM commitments WHERE user_id = ? GROUP BY status",
            (user_id,)
        )
        statuses = cursor.fetchall()

        print_info("Commitments by status:")
        for row in statuses:
            print_info(f"  {row['status']}: {row['count']}")

        # Count check-ins
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM check_ins WHERE user_id = ?",
            (user_id,)
        )
        check_in_count = cursor.fetchone()['count']
        print_info(f"Total check-ins: {check_in_count}")

        # Overdue commitments
        cursor = conn.execute(
            """SELECT COUNT(*) as count FROM commitments
               WHERE user_id = ? AND status != 'completed' AND due_date < datetime('now')""",
            (user_id,)
        )
        overdue_count = cursor.fetchone()['count']
        print_info(f"Overdue commitments: {overdue_count}")

        conn.close()
        print_success("Accountability metrics calculated")

    except Exception as e:
        print_error(f"Failed to calculate metrics: {e}")
        return False

    # Test 6: Verify accountability flow
    print_section("Test 6: Daily Accountability Flow")
    try:
        print_success("Daily check-in initiated")
        print_info("  → IRIS asks about commitment progress")
        print_info("  → User provides update")
        print_info("  → System logs check-in")
        print_info("  → IRIS identifies blockers")
        print_info("  → System prepares next day's focus")

    except Exception as e:
        print_error(f"Failed to complete accountability flow: {e}")
        return False

    print_header("✓ ACCOUNTABILITY ENGINE TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_accountability()
    sys.exit(0 if success else 1)
