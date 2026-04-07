#!/usr/bin/env python3
"""
IRIS Core -- Test Calendar Generation
Tests PNG and ICS file generation from Mt. Everest summary.
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import print_header, print_section, print_success, print_error, print_info
from calendar_generator import parse_milestones, generate_calendar_png, generate_ics


def test_calendar_generation():
    """Test calendar PNG and ICS file generation."""

    print_header("IRIS CORE - CALENDAR GENERATION TEST")

    # Sample summary (same format as bot produces)
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

    print_section("Testing Milestone Parsing")
    try:
        milestones = parse_milestones(summary)
        print_success("Milestones parsed")
        print_info(f"Goal: {milestones['goal']}")
        print_info(f"Why: {milestones['why']}")
        print_info(f"Ceiling: {milestones['ceiling']}")
        print_info(f"12-Month: {milestones['milestones'].get('twelve_month', 'N/A')}")
        print_info(f"90-Day: {milestones['milestones'].get('ninety_day', 'N/A')}")
        print_info(f"This Month: {milestones['milestones'].get('this_month', 'N/A')}")
    except Exception as e:
        print_error(f"Failed to parse milestones: {e}")
        return False

    print_section("Testing Calendar PNG Generation")
    try:
        calendar_png = generate_calendar_png(summary)
        if calendar_png and len(calendar_png) > 0:
            print_success(f"Calendar PNG generated ({len(calendar_png)} bytes)")
            # Save for inspection
            output_path = Path(__file__).parent.parent / "data" / "test_calendar.png"
            output_path.write_bytes(calendar_png)
            print_info(f"Saved to: {output_path}")
        else:
            print_error("Calendar PNG generation returned empty")
            return False
    except Exception as e:
        print_error(f"Failed to generate calendar PNG: {e}")
        return False

    print_section("Testing ICS File Generation")
    try:
        ics_content = generate_ics(summary)
        if ics_content and len(ics_content) > 0:
            print_success(f"ICS file generated ({len(ics_content)} bytes)")
            # Save for inspection
            output_path = Path(__file__).parent.parent / "data" / "test_calendar.ics"
            output_path.write_text(ics_content)
            print_info(f"Saved to: {output_path}")
            print_section("ICS Preview (first 500 chars)")
            print(ics_content[:500])
        else:
            print_error("ICS generation returned empty")
            return False
    except Exception as e:
        print_error(f"Failed to generate ICS: {e}")
        return False

    print_header("✓ CALENDAR GENERATION TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_calendar_generation()
    sys.exit(0 if success else 1)
