#!/usr/bin/env python3
"""
Car Wash Site Evaluation System
Evaluates potential car wash locations against the 4 Pillars criteria
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
GOOGLE_MAPS_API_KEY = None  # Set this when you get your API key

# Scoring rubric - EXACT from PDF
SCORING_CRITERIA = {
    "population": {
        "30000+": 1
    },
    "competition": {
        "0-1": 1,
        "2+": 0
    },
    "household_income": {
        "50000-75000": 1,
        "75000+": 2
    },
    "aadt": {
        "13000-15000": 1,
        "15000+": 2
    },
    "going_home_side": {
        "yes": 1,
        "no": 0
    },
    "multifamily_adjacent": {
        "yes": 1,
        "no": 0
    },
    "speed_limit": {
        "25-35": 1,
        "35+": 0
    },
    "retail_adjacent": {
        "yes": 1,
        "no": 0
    },
    "zoning": {
        "permitted": 1,
        "not_permitted": 0
    },
    "size": {
        "0.5-0.75": 1,
        "0.75-1.0": 2,
        "1.0+": 0
    },
    "frontage": {
        "65-100": 0,
        "100+": 1
    },
    "price": {
        "0-500000": 2,
        "500000-1000000": 1,
        "1000000+": 0
    }
}

# Required 4 Pillars qualifiers
REQUIRED_QUALIFIERS = {
    "population": 30000,
    "median_income": 50000,
    "aadt": 13000,
    "parcel_size_min": 0.5,
    "parcel_size_max": 1.0,
    "max_competitors": 1
}

class ListingData:
    """Data from the listing itself"""
    def __init__(self, address: str, price: float, parcel_size: float, 
                 frontage: float, zoning: str):
        self.address = address
        self.price = price
        self.parcel_size = parcel_size
        self.frontage = frontage
        self.zoning = zoning

class ResearchData:
    """Data from automated research"""
    def __init__(self):
        self.population: Optional[int] = None
        self.median_income: Optional[int] = None
        self.aadt: Optional[int] = None
        self.speed_limit: Optional[int] = None
        self.competitors_count: Optional[int] = None
        self.competitors_list: list = []
        self.multifamily_adjacent: Optional[bool] = None
        self.retail_adjacent: Optional[bool] = None
        self.going_home_side: Optional[bool] = None
        self.lat: Optional[float] = None
        self.lng: Optional[float] = None

def check_required_qualifiers(listing: ListingData, research: ResearchData) -> tuple[bool, list]:
    """Check if site meets all 4 Pillars required qualifiers"""
    failures = []
    
    if research.population is None or research.population < REQUIRED_QUALIFIERS["population"]:
        failures.append(f"Population {research.population} < 30,000 required")
    
    if research.median_income is None or research.median_income < REQUIRED_QUALIFIERS["median_income"]:
        failures.append(f"Median income ${research.median_income:,} < $50,000 required")
    
    if research.aadt is None or research.aadt < REQUIRED_QUALIFIERS["aadt"]:
        failures.append(f"AADT {research.aadt:,} < 13,000 required")
    
    if listing.parcel_size < REQUIRED_QUALIFIERS["parcel_size_min"] or listing.parcel_size > REQUIRED_QUALIFIERS["parcel_size_max"]:
        failures.append(f"Parcel size {listing.parcel_size} acres not in 0.5-1.0 acre range")
    
    if research.competitors_count is None or research.competitors_count > REQUIRED_QUALIFIERS["max_competitors"]:
        failures.append(f"{research.competitors_count} competitors > 1 allowed within 1 mile")
    
    return len(failures) == 0, failures

def score_listing(listing: ListingData, research: ResearchData) -> Dict[str, Any]:
    """Score listing according to exact rubric"""
    scores = {}
    total = 0
    
    # Population
    if research.population and research.population >= 30000:
        scores["population"] = 1
        total += 1
    else:
        scores["population"] = 0
    
    # Competition
    if research.competitors_count is not None:
        if research.competitors_count <= 1:
            scores["competition"] = 1
            total += 1
        else:
            scores["competition"] = 0
    else:
        scores["competition"] = 0
    
    # Household Income
    if research.median_income:
        if research.median_income >= 75000:
            scores["household_income"] = 2
            total += 2
        elif research.median_income >= 50000:
            scores["household_income"] = 1
            total += 1
        else:
            scores["household_income"] = 0
    else:
        scores["household_income"] = 0
    
    # AADT
    if research.aadt:
        if research.aadt >= 15000:
            scores["aadt"] = 2
            total += 2
        elif research.aadt >= 13000:
            scores["aadt"] = 1
            total += 1
        else:
            scores["aadt"] = 0
    else:
        scores["aadt"] = 0
    
    # Going Home Side
    if research.going_home_side:
        scores["going_home_side"] = 1
        total += 1
    else:
        scores["going_home_side"] = 0
    
    # Multifamily Adjacent
    if research.multifamily_adjacent:
        scores["multifamily_adjacent"] = 1
        total += 1
    else:
        scores["multifamily_adjacent"] = 0
    
    # Speed Limit - EXACT per rubric: 25-35 MPH = 1 pt, 35+ MPH = 0 pts
    if research.speed_limit:
        if 25 <= research.speed_limit <= 35:
            scores["speed_limit"] = 1
            total += 1
        else:
            scores["speed_limit"] = 0
    else:
        scores["speed_limit"] = 0
    
    # Retail Adjacent
    if research.retail_adjacent:
        scores["retail_adjacent"] = 1
        total += 1
    else:
        scores["retail_adjacent"] = 0
    
    # Zoning - check if it's a permitted use
    permitted_zones = ["C-2", "B-2", "C2", "B2"]
    if any(zone.upper() in listing.zoning.upper() for zone in permitted_zones):
        scores["zoning"] = 1
        total += 1
    else:
        scores["zoning"] = 0
    
    # Size
    if listing.parcel_size >= 0.75 and listing.parcel_size <= 1.0:
        scores["size"] = 2
        total += 2
    elif listing.parcel_size >= 0.5 and listing.parcel_size < 0.75:
        scores["size"] = 1
        total += 1
    else:
        scores["size"] = 0
    
    # Frontage
    if listing.frontage >= 100:
        scores["frontage"] = 1
        total += 1
    else:
        scores["frontage"] = 0
    
    # Price
    if listing.price <= 500000:
        scores["price"] = 2
        total += 2
    elif listing.price <= 1000000:
        scores["price"] = 1
        total += 1
    else:
        scores["price"] = 0
    
    return {
        "breakdown": scores,
        "total": total,
        "max_possible": 16
    }

def get_rating(score: int) -> tuple[str, str]:
    """Get rating category based on score"""
    if score >= 12:
        return "Best", "Strong candidate for acquisition"
    elif score >= 8:
        return "Better", "May need review or additional factors"
    else:
        return "Good", "Likely not suitable for development"

def generate_report(listing: ListingData, research: ResearchData, 
                   passes_qualifiers: bool, qualifier_failures: list,
                   scoring_result: Dict[str, Any]) -> str:
    """Generate markdown evaluation report"""
    
    rating, description = get_rating(scoring_result["total"])
    
    report = f"""# Car Wash Site Evaluation Report

**Address:** {listing.address}  
**Date:** {datetime.now().strftime("%B %d, %Y")}  
**Evaluation ID:** {datetime.now().strftime("%Y%m%d-%H%M%S")}

---

## Quick Verdict

"""
    
    if passes_qualifiers:
        report += f"""✅ **PASS** - Score: {scoring_result["total"]}/{scoring_result["max_possible"]} ({rating})  
**{description}**

"""
    else:
        report += f"""❌ **FAIL** - Does not meet required 4 Pillars qualifiers

**Disqualifying factors:**
"""
        for failure in qualifier_failures:
            report += f"- {failure}\n"
        report += "\n"
    
    # 4 Pillars Check
    report += """## 4 Pillars Required Qualifiers

| Pillar | Requirement | Result | Status |
|--------|-------------|--------|--------|
"""
    
    pop_status = "✅" if research.population and research.population >= 30000 else "❌"
    report += f"| Population | 30,000+ | {research.population:,} | {pop_status} |\n"
    
    comp_status = "✅" if research.competitors_count is not None and research.competitors_count <= 1 else "❌"
    report += f"| Competition | ≤1 within 1 mile | {research.competitors_count} found | {comp_status} |\n"
    
    traffic_status = "✅" if research.aadt and research.aadt >= 13000 else "❌"
    aadt_display = f"{research.aadt:,}" if research.aadt else "Unknown"
    report += f"| Traffic (AADT) | 13,000+ | {aadt_display} | {traffic_status} |\n"
    
    parcel_status = "✅" if 0.5 <= listing.parcel_size <= 1.0 else "❌"
    report += f"| Parcel Size | 0.5-1.0 acres | {listing.parcel_size} acres | {parcel_status} |\n"
    
    income_status = "✅" if research.median_income and research.median_income >= 50000 else "❌"
    income_display = f"${research.median_income:,}" if research.median_income else "Unknown"
    report += f"| Median Income | $50,000+ | {income_display} | {income_status} |\n"
    
    report += "\n"
    
    # Detailed Scoring Breakdown
    report += """## Detailed Scoring Breakdown

| Criterion | Result | Points Awarded | Max Points |
|-----------|--------|----------------|------------|
"""
    
    scores = scoring_result["breakdown"]
    
    # Population
    pop_display = f"{research.population:,}" if research.population else "Unknown"
    report += f"| Population 30,000+ | {pop_display} | {scores['population']} | 1 |\n"
    
    # Competition
    comp_display = f"{research.competitors_count} competitors" if research.competitors_count is not None else "Unknown"
    report += f"| Competition ≤1 | {comp_display} | {scores['competition']} | 1 |\n"
    
    # Income
    income_bracket = ""
    if research.median_income:
        if research.median_income >= 75000:
            income_bracket = f"${research.median_income:,} (≥$75K)"
        elif research.median_income >= 50000:
            income_bracket = f"${research.median_income:,} ($50K-$75K)"
        else:
            income_bracket = f"${research.median_income:,} (<$50K)"
    else:
        income_bracket = "Unknown"
    report += f"| Household Income | {income_bracket} | {scores['household_income']} | 2 |\n"
    
    # AADT
    aadt_bracket = ""
    if research.aadt:
        if research.aadt >= 15000:
            aadt_bracket = f"{research.aadt:,} (≥15K)"
        elif research.aadt >= 13000:
            aadt_bracket = f"{research.aadt:,} (13K-15K)"
        else:
            aadt_bracket = f"{research.aadt:,} (<13K)"
    else:
        aadt_bracket = "Unknown"
    report += f"| AADT | {aadt_bracket} | {scores['aadt']} | 2 |\n"
    
    # Going Home Side
    going_home_display = "YES" if research.going_home_side else "NO/Unknown"
    report += f"| Going Home Side | {going_home_display} | {scores['going_home_side']} | 1 |\n"
    
    # Multifamily Adjacent
    multifam_display = "YES" if research.multifamily_adjacent else "NO/Unknown"
    report += f"| Multifamily Adjacent | {multifam_display} | {scores['multifamily_adjacent']} | 1 |\n"
    
    # Speed Limit
    speed_display = f"{research.speed_limit} MPH" if research.speed_limit else "Unknown"
    if research.speed_limit:
        if 25 <= research.speed_limit <= 35:
            speed_display += " (25-35 MPH ✓)"
        else:
            speed_display += " (outside 25-35 MPH range)"
    report += f"| Speed Limit | {speed_display} | {scores['speed_limit']} | 1 |\n"
    
    # Retail Adjacent
    retail_display = "YES" if research.retail_adjacent else "NO/Unknown"
    report += f"| Retail Adjacent | {retail_display} | {scores['retail_adjacent']} | 1 |\n"
    
    # Zoning
    zoning_display = f"{listing.zoning} ✓" if scores['zoning'] == 1 else f"{listing.zoning} (not permitted)"
    report += f"| Zoning | {zoning_display} | {scores['zoning']} | 1 |\n"
    
    # Size
    size_bracket = ""
    if listing.parcel_size >= 0.75 and listing.parcel_size <= 1.0:
        size_bracket = f"{listing.parcel_size} acres (0.75-1.0)"
    elif listing.parcel_size >= 0.5 and listing.parcel_size < 0.75:
        size_bracket = f"{listing.parcel_size} acres (0.5-0.75)"
    else:
        size_bracket = f"{listing.parcel_size} acres (out of range)"
    report += f"| Size | {size_bracket} | {scores['size']} | 2 |\n"
    
    # Frontage
    frontage_display = f"{listing.frontage} ft" + (" (≥100 ft)" if listing.frontage >= 100 else " (<100 ft)")
    report += f"| Frontage | {frontage_display} | {scores['frontage']} | 1 |\n"
    
    # Price
    price_bracket = ""
    if listing.price <= 500000:
        price_bracket = f"${listing.price:,} (≤$500K)"
    elif listing.price <= 1000000:
        price_bracket = f"${listing.price:,} ($500K-$1M)"
    else:
        price_bracket = f"${listing.price:,} (>$1M)"
    report += f"| Price | {price_bracket} | {scores['price']} | 2 |\n"
    
    report += f"| **TOTAL SCORE** | | **{scoring_result['total']}** | **{scoring_result['max_possible']}** |\n\n"
    
    # Competitor Details
    if research.competitors_list:
        report += "## Competitor Analysis\n\n"
        report += f"Found {len(research.competitors_list)} car wash(es) within 1-mile radius:\n\n"
        for i, comp in enumerate(research.competitors_list, 1):
            report += f"{i}. {comp}\n"
        report += "\n"
    
    # Recommendations
    report += "## Recommendations\n\n"
    if passes_qualifiers:
        if scoring_result['total'] >= 12:
            report += """**Strong Acquisition Candidate**

Next steps:
1. Schedule site visit to verify traffic patterns
2. Request formal traffic study from city/county
3. Verify zoning with planning department
4. Assess competition quality and service offerings
5. Review property title and environmental reports

"""
        elif scoring_result['total'] >= 8:
            report += """**Requires Additional Review**

Next steps:
1. Identify specific weaknesses from scoring breakdown
2. Determine if weaknesses are addressable
3. Request additional market data
4. Compare to other available opportunities

"""
        else:
            report += """**Marginal Opportunity**

This site passes minimum qualifiers but scores low overall. Consider:
1. Whether unique factors make it more attractive than score suggests
2. If comparable alternatives are available
3. If price negotiation could improve ROI

"""
    else:
        report += "**Do Not Pursue** - Site does not meet required qualifiers.\n\n"
    
    return report

if __name__ == "__main__":
    print("Car Wash Site Evaluator - Ready")
    print("\nThis script will be integrated with research automation.")
    print("For now, it demonstrates the scoring logic.")
