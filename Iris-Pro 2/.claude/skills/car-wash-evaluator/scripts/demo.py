#!/usr/bin/env python3
"""
Demo: Car Wash Site Evaluator
Shows the scoring system in action with sample data
"""

from carwash_evaluator import (
    ListingData, ResearchData, check_required_qualifiers,
    score_listing, generate_report
)

def demo_strong_candidate():
    """Demo: Strong acquisition candidate (14/16 points)"""
    
    print("=" * 70)
    print("DEMO: Strong Acquisition Candidate".center(70))
    print("=" * 70)
    
    # Listing data
    listing = ListingData(
        address="456 Commerce Blvd, Orlando, FL 32801",
        price=750000,
        parcel_size=0.85,
        frontage=120,
        zoning="C-2"
    )
    
    # Research data (strong opportunity)
    research = ResearchData()
    research.population = 42500
    research.median_income = 68000
    research.aadt = 18200
    research.speed_limit = 30
    research.competitors_count = 0
    research.competitors_list = []
    research.multifamily_adjacent = True
    research.retail_adjacent = True
    research.going_home_side = True
    
    # Evaluate
    passes, failures = check_required_qualifiers(listing, research)
    scoring_result = score_listing(listing, research)
    report = generate_report(listing, research, passes, failures, scoring_result)
    
    print(report)
    return scoring_result["total"]


def demo_marginal_opportunity():
    """Demo: Marginal opportunity (7/16 points)"""
    
    print("\n" + "=" * 70)
    print("DEMO: Marginal Opportunity".center(70))
    print("=" * 70)
    
    # Listing data
    listing = ListingData(
        address="789 Highway 50, Winter Park, FL 32789",
        price=1200000,
        parcel_size=1.2,  # Too big
        frontage=85,      # Too small
        zoning="C-2"
    )
    
    # Research data (weak opportunity)
    research = ResearchData()
    research.population = 32000
    research.median_income = 52000
    research.aadt = 14000
    research.speed_limit = 45  # Too fast
    research.competitors_count = 1
    research.competitors_list = ["QuickWash Express - 0.6 miles"]
    research.multifamily_adjacent = False
    research.retail_adjacent = False
    research.going_home_side = False
    
    # Evaluate
    passes, failures = check_required_qualifiers(listing, research)
    scoring_result = score_listing(listing, research)
    report = generate_report(listing, research, passes, failures, scoring_result)
    
    print(report)
    return scoring_result["total"]


def demo_disqualified():
    """Demo: Fails required qualifiers"""
    
    print("\n" + "=" * 70)
    print("DEMO: Disqualified (Fails Required Qualifiers)".center(70))
    print("=" * 70)
    
    # Listing data
    listing = ListingData(
        address="321 Rural Road, Apopka, FL 32703",
        price=450000,
        parcel_size=0.6,
        frontage=110,
        zoning="C-2"
    )
    
    # Research data (fails qualifiers)
    research = ResearchData()
    research.population = 18000  # FAIL: < 30,000
    research.median_income = 42000  # FAIL: < $50,000
    research.aadt = 9500  # FAIL: < 13,000
    research.speed_limit = 30
    research.competitors_count = 3  # FAIL: > 1
    research.competitors_list = [
        "Wash World - 0.3 miles",
        "Sparkle Shine - 0.7 miles",
        "Auto Spa - 0.9 miles"
    ]
    research.multifamily_adjacent = False
    research.retail_adjacent = True
    research.going_home_side = True
    
    # Evaluate
    passes, failures = check_required_qualifiers(listing, research)
    scoring_result = score_listing(listing, research)
    report = generate_report(listing, research, passes, failures, scoring_result)
    
    print(report)
    return scoring_result["total"]


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + "CAR WASH SITE EVALUATOR - DEMONSTRATION".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print("\nThis demo shows how the scoring system evaluates three different")
    print("listing scenarios using the exact rubric from your PDF.\n")
    
    input("Press Enter to see Demo 1: Strong Candidate...")
    score1 = demo_strong_candidate()
    
    input("\nPress Enter to see Demo 2: Marginal Opportunity...")
    score2 = demo_marginal_opportunity()
    
    input("\nPress Enter to see Demo 3: Disqualified Site...")
    score3 = demo_disqualified()
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE".center(70))
    print("=" * 70)
    print(f"\nDemo 1 Score: {score1}/16 (Strong candidate)")
    print(f"Demo 2 Score: {score2}/16 (Marginal)")
    print(f"Demo 3: Disqualified (fails required qualifiers)")
    print("\nRun 'python evaluate.py' to evaluate real listings.")
    print("=" * 70 + "\n")
