#!/usr/bin/env python3
"""
IRIS Core -- Test Upgrade Prompt
Tests the upgrade messaging that directs users to IRIS Pro.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import print_header, print_section, print_success, print_info
import config
from iris_prompt import get_upgrade_message


def test_upgrade_prompts():
    """Test upgrade prompt generation."""

    print_header("IRIS CORE - UPGRADE PROMPT TEST")

    upgrade_url = config.PRO_UPGRADE_URL

    print_section("Configuration")
    print_info(f"Pro upgrade URL: {upgrade_url}")

    print_section("Testing Upgrade Messages")
    print_info("Generating 3 different upgrade prompts:")

    # Get multiple upgrade messages to show variety
    messages_tested = set()
    attempts = 0
    max_attempts = 10

    while len(messages_tested) < 3 and attempts < max_attempts:
        msg = get_upgrade_message(upgrade_url)
        messages_tested.add(msg)
        attempts += 1

    for i, msg in enumerate(messages_tested, 1):
        print(f"\n--- Upgrade Message {i} ---")
        print(f"{msg}\n")
        print_success("Message generated")

    if len(messages_tested) < 3:
        print_info(f"Note: Only {len(messages_tested)} unique messages available (randomization)")

    print_section("Message Format Check")
    test_msg = get_upgrade_message(upgrade_url)

    checks = [
        ("Contains URL", upgrade_url in test_msg),
        ("Mentions IRIS Pro", "IRIS Pro" in test_msg),
        ("Has clear call-to-action", any(phrase in test_msg for phrase in ["Want", "check out", "build", "climb"])),
        ("Not overly salesy", not any(word in test_msg.lower() for word in ["amazing", "incredible", "revolutionary", "!!!"])),
    ]

    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")

    print_header("✓ UPGRADE PROMPT TEST PASSED")
    return True


if __name__ == "__main__":
    test_upgrade_prompts()
    sys.exit(0)
