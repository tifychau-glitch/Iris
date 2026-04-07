#!/usr/bin/env python3
"""
IRIS Pro -- Full User Journey Test
Runs all tests in sequence to simulate complete user experience.
"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import print_header, print_section, print_success, print_error

# Test script files in execution order
TEST_SCRIPTS = [
    ("Onboarding", "test_onboarding.py"),
    ("Dashboard", "test_dashboard.py"),
    ("Accountability Engine", "test_accountability.py"),
    ("Cron Jobs", "test_cron_jobs.py"),
    ("Upgrade Flow", "test_upgrade_flow.py"),
]


def run_full_journey():
    """Run all tests in sequence."""

    print_header("IRIS PRO - FULL USER JOURNEY TEST")

    script_dir = Path(__file__).parent
    results = []
    all_passed = True

    for test_name, script_file in TEST_SCRIPTS:
        print_section(f"Running: {test_name}")

        script_path = script_dir / script_file
        if not script_path.exists():
            print_error(f"Test script not found: {script_file}")
            results.append((test_name, False))
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
                results.append((test_name, True))
            else:
                print_error(f"{test_name} failed")
                results.append((test_name, False))
                all_passed = False

                # Show output for debugging
                if result.stdout:
                    print("\n--- Output ---")
                    print(result.stdout[-500:])  # Last 500 chars
                if result.stderr:
                    print("\n--- Errors ---")
                    print(result.stderr[-500:])

        except subprocess.TimeoutExpired:
            print_error(f"{test_name} timed out")
            results.append((test_name, False))
            all_passed = False
        except Exception as e:
            print_error(f"{test_name} exception: {e}")
            results.append((test_name, False))
            all_passed = False

    # Summary
    print_section("Test Summary")
    for test_name, passed in results:
        status = "✓" if passed else "✗"
        print(f"{status} {test_name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"\nPassed: {passed_count}/{total_count}")

    if all_passed:
        print_header("✓ ALL TESTS PASSED - FULL JOURNEY COMPLETE")
        return True
    else:
        print_header("✗ SOME TESTS FAILED - SEE ABOVE")
        return False


if __name__ == "__main__":
    success = run_full_journey()
    sys.exit(0 if success else 1)
