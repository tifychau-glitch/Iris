#!/usr/bin/env python3
"""
IRIS Core -- Full User Journey Test
Runs all tests in sequence to simulate a complete user experience.
"""

import sys
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import print_header, print_section, print_success, print_error, print_info

# Test script files
TEST_SCRIPTS = [
    ("Bot Conversation", "test_bot_conversation.py"),
    ("Calendar Generation", "test_calendar.py"),
    ("Email Sending", "test_email.py"),
    ("Upgrade Prompt", "test_upgrade_prompt.py"),
]


def run_full_journey():
    """Run all tests in sequence."""

    print_header("IRIS CORE - FULL USER JOURNEY TEST")

    script_dir = Path(__file__).parent
    all_passed = True

    for test_name, script_file in TEST_SCRIPTS:
        print_section(f"Running: {test_name}")

        script_path = script_dir / script_file
        if not script_path.exists():
            print_error(f"Test script not found: {script_file}")
            all_passed = False
            continue

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print_success(f"{test_name} passed")
            else:
                print_error(f"{test_name} failed")
                print("\n--- Output ---")
                print(result.stdout)
                if result.stderr:
                    print("\n--- Errors ---")
                    print(result.stderr)
                all_passed = False

        except subprocess.TimeoutExpired:
            print_error(f"{test_name} timed out")
            all_passed = False
        except Exception as e:
            print_error(f"{test_name} exception: {e}")
            all_passed = False

    print_section("Test Summary")
    passed = sum(1 for _, script in TEST_SCRIPTS if True)  # All were attempted

    if all_passed:
        print_header("✓ ALL TESTS PASSED - FULL JOURNEY COMPLETE")
        return True
    else:
        print_header("✗ SOME TESTS FAILED - SEE ABOVE")
        return False


if __name__ == "__main__":
    success = run_full_journey()
    sys.exit(0 if success else 1)
