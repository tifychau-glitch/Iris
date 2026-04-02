#!/usr/bin/env python3
"""
Car Wash Site Evaluator - Integrated Version
Complete workflow with automated research via Claude API
"""

import sys
import os
from datetime import datetime

# Check for required imports
try:
    from claude_research import research_site_with_claude, ResearchData
    CLAUDE_AVAILABLE = True
except ImportError:
    print("[!] Claude API module not fully set up")
    CLAUDE_AVAILABLE = False
    
    class ResearchData:
        def __init__(self):
            self.population = None
            self.median_income = None
            self.aadt = None
            self.speed_limit = None
            self.competitors_count = None
            self.competitors_list = []
            self.multifamily_adjacent = None
            self.retail_adjacent = None
            self.going_home_side = None

from carwash_evaluator import (
    ListingData, check_required_qualifiers,
    score_listing, generate_report
)


def get_listing_input() -> ListingData:
    """Interactive input for listing data"""
    print("\n" + "=" * 70)
    print("CAR WASH SITE EVALUATOR".center(70))
    print("=" * 70)
    print("\nEnter listing details:\n")
    
    address = input("Full Address: ").strip()
    
    while True:
        try:
            price_input = input("Price ($): ").strip().replace("$", "").replace(",", "")
            price = float(price_input)
            break
        except ValueError:
            print("  Invalid. Enter numbers only (e.g., 750000)")
    
    while True:
        try:
            parcel_size = float(input("Parcel Size (acres): ").strip())
            break
        except ValueError:
            print("  Invalid. Enter a number (e.g., 0.8)")
    
    while True:
        try:
            frontage = float(input("Frontage (feet): ").strip())
            break
        except ValueError:
            print("  Invalid. Enter a number (e.g., 120)")
    
    zoning = input("Zoning (e.g., C-2, B-2): ").strip()
    
    return ListingData(address, price, parcel_size, frontage, zoning)


def manual_research_input(address: str) -> ResearchData:
    """Manual input of research data"""
    print(f"\n" + "=" * 70)
    print("RESEARCH DATA INPUT (Manual Mode)".center(70))
    print("=" * 70)
    print(f"\nEnter research data for: {address}\n")
    
    research = ResearchData()
    
    # Population
    while True:
        try:
            pop_input = input("Population (within 1-3 mile radius): ").strip().replace(",", "")
            if pop_input:
                research.population = int(pop_input)
            break
        except ValueError:
            print("  Invalid. Enter a number or press Enter to skip")
    
    # Median Income
    while True:
        try:
            income_input = input("Median Household Income ($): ").strip().replace("$", "").replace(",", "")
            if income_input:
                research.median_income = int(income_input)
            break
        except ValueError:
            print("  Invalid. Enter a number or press Enter to skip")
    
    # AADT
    while True:
        try:
            aadt_input = input("AADT (traffic count): ").strip().replace(",", "")
            if aadt_input:
                research.aadt = int(aadt_input)
            break
        except ValueError:
            print("  Invalid. Enter a number or press Enter to skip")
    
    # Speed Limit
    while True:
        try:
            speed_input = input("Speed Limit (MPH): ").strip()
            if speed_input:
                research.speed_limit = int(speed_input)
            break
        except ValueError:
            print("  Invalid. Enter a number or press Enter to skip")
    
    # Competitors
    while True:
        try:
            comp_input = input("Number of car washes within 1 mile: ").strip()
            if comp_input:
                research.competitors_count = int(comp_input)
                if research.competitors_count > 0:
                    print("  Enter competitor names (or press Enter to skip):")
                    research.competitors_list = []
                    for i in range(research.competitors_count):
                        name = input(f"    Competitor {i+1}: ").strip()
                        if name:
                            research.competitors_list.append(name)
            else:
                research.competitors_count = 0
            break
        except ValueError:
            print("  Invalid. Enter a number")
    
    # Adjacent properties
    multifam = input("Multifamily housing adjacent? (y/n): ").strip().lower()
    research.multifamily_adjacent = multifam == 'y'
    
    retail = input("Retail adjacent? (y/n): ").strip().lower()
    research.retail_adjacent = retail == 'y'
    
    going_home = input("On 'going home' side of traffic? (y/n): ").strip().lower()
    research.going_home_side = going_home == 'y'
    
    return research


def main():
    """Main evaluation workflow"""
    
    # Step 1: Get listing data
    listing = get_listing_input()
    
    # Step 2: Choose research method
    print("\n" + "=" * 70)
    print("RESEARCH METHOD SELECTION".center(70))
    print("=" * 70)
    
    # Check if Claude API is available
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if CLAUDE_AVAILABLE and api_key:
        print("\n✓ Claude API detected")
        print("\n1. Automated Research (Claude API + Web Search)")
        print("2. Manual Input (you provide research data)")
        print("\nRecommended: Option 1 (automated)")
    else:
        print("\n! Claude API not configured")
        print("\nTo enable automated research:")
        print("1. Install: pip install anthropic")
        print("2. Set: export ANTHROPIC_API_KEY='your-api-key'")
        print("\nProceeding with manual input...\n")
    
    # Get research data
    if CLAUDE_AVAILABLE and api_key:
        choice = input("\nSelect method (1 or 2): ").strip()
        if choice == "1":
            try:
                research = research_site_with_claude(listing.address, api_key)
            except Exception as e:
                print(f"\n[✗] Automated research failed: {e}")
                print("[!] Falling back to manual input\n")
                research = manual_research_input(listing.address)
        else:
            research = manual_research_input(listing.address)
    else:
        research = manual_research_input(listing.address)
    
    # Step 3: Evaluate
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS".center(70))
    print("=" * 70 + "\n")
    
    # Check qualifiers
    passes, failures = check_required_qualifiers(listing, research)
    
    # Score
    scoring_result = score_listing(listing, research)
    
    # Generate report
    report = generate_report(listing, research, passes, failures, scoring_result)
    
    # Display
    print(report)
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_address = "".join(c if c.isalnum() or c == ' ' else '_' for c in listing.address[:40])
    safe_address = safe_address.replace(' ', '_')
    filename = f"carwash_eval_{safe_address}_{timestamp}.md"
    
    filepath = f"/mnt/user-data/outputs/{filename}"
    
    try:
        with open(filepath, 'w') as f:
            f.write(report)
        print(f"\n{'=' * 70}")
        print(f"✓ Report saved: {filename}".center(70))
        print(f"{'=' * 70}\n")
    except Exception as e:
        print(f"\n[!] Could not save report: {e}")
        print(f"[!] Report printed above\n")
    
    return filepath


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n[!] Cancelled by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[✗] Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
