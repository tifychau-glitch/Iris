#!/usr/bin/env python3
"""
Claude API integration for automated car wash site research
Uses web_search tool to gather all required data points
"""

import json
import os
from typing import Dict, Any, Optional
import anthropic

# Will be imported from main evaluator
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


def research_site_with_claude(address: str, api_key: Optional[str] = None) -> ResearchData:
    """
    Use Claude API with web_search to research a car wash site
    
    Args:
        address: Full address to research
        api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
    
    Returns:
        ResearchData object with all findings
    """
    
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Research prompt for Claude
    research_prompt = f"""I need comprehensive research on a potential car wash location for site evaluation. Please research this address thoroughly:

**Address:** {address}

**Required Data Points:**

1. **Population** 
   - Total population within 1-3 mile radius of this address
   - Use census data or demographic databases

2. **Median Household Income**
   - Median household income for the census tract or zip code containing this address
   - Use US Census Bureau data

3. **AADT (Annual Average Daily Traffic)**
   - Traffic count on the specific road where this property is located
   - Check state DOT traffic count databases or transportation studies
   - If exact AADT not available, estimate based on road classification

4. **Speed Limit**
   - Posted speed limit in MPH on the road at this specific location
   - Check Google Maps, local traffic data, or mapping services

5. **Car Wash Competitors**
   - Find ALL car washes within a 1-mile radius
   - Provide business name and approximate distance
   - Count the total number

6. **Adjacent Property Assessment**
   - Multifamily: Are there apartments, condos, or multifamily housing immediately adjacent (within ~200 feet)?
   - Retail: Are there stores, shopping centers, or retail businesses immediately adjacent?

7. **Traffic Flow Direction ("Going Home Side")**
   - Identify the nearest major residential areas (where people live)
   - Identify the nearest employment centers or downtown area (where people work)
   - Determine the primary PM commute direction (work → home)
   - Assess whether this property location catches PM commute traffic (evening rush going home)
   - Important: People wash cars on the way HOME, not on the way TO work

**Instructions:**
- Use web search extensively to find accurate current data
- Cite your sources
- If data is unavailable, state this clearly
- Provide confidence level (high/medium/low) for each finding

**Output Format:**
Provide your research findings in this exact JSON structure:

{{
    "population": {{
        "value": <number or null>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "median_income": {{
        "value": <number or null>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "aadt": {{
        "value": <number or null>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "speed_limit": {{
        "value": <number or null>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "competitors": {{
        "count": <number>,
        "list": ["Name 1 - distance", "Name 2 - distance"],
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "multifamily_adjacent": {{
        "value": <true or false>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "retail_adjacent": {{
        "value": <true or false>,
        "confidence": "high|medium|low",
        "source": "brief source description"
    }},
    "going_home_side": {{
        "value": <true or false>,
        "confidence": "high|medium|low",
        "source": "brief source description",
        "explanation": "brief explanation of traffic flow analysis"
    }}
}}

Only return the JSON, no additional text."""

    print(f"[→] Calling Claude API to research: {address}")
    print(f"[→] This will use web search to gather all data points...")
    print(f"[→] This may take 30-90 seconds...\n")
    
    try:
        # Call Claude API with web search tool enabled
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=[{
                "role": "user",
                "content": research_prompt
            }]
        )
        
        # Extract the response
        # Claude may return multiple content blocks (text + tool use results)
        full_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                full_text += block.text
        
        print(f"[✓] Claude API response received\n")
        
        # Parse the JSON response
        research_data = _parse_claude_response(full_text)
        
        return research_data
        
    except anthropic.APIError as e:
        print(f"[✗] Claude API error: {e}")
        raise
    except Exception as e:
        print(f"[✗] Unexpected error: {e}")
        raise


def _parse_claude_response(response_text: str) -> ResearchData:
    """Parse Claude's JSON response into ResearchData object"""
    
    research = ResearchData()
    
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_text = response_text.strip()
        if json_text.startswith("```json"):
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif json_text.startswith("```"):
            json_text = json_text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(json_text)
        
        # Population
        if "population" in data and data["population"]["value"] is not None:
            research.population = int(data["population"]["value"])
            print(f"[✓] Population: {research.population:,} ({data['population']['confidence']} confidence)")
        else:
            print(f"[!] Population: Not found")
        
        # Median Income
        if "median_income" in data and data["median_income"]["value"] is not None:
            research.median_income = int(data["median_income"]["value"])
            print(f"[✓] Median Income: ${research.median_income:,} ({data['median_income']['confidence']} confidence)")
        else:
            print(f"[!] Median Income: Not found")
        
        # AADT
        if "aadt" in data and data["aadt"]["value"] is not None:
            research.aadt = int(data["aadt"]["value"])
            print(f"[✓] AADT: {research.aadt:,} ({data['aadt']['confidence']} confidence)")
        else:
            print(f"[!] AADT: Not found")
        
        # Speed Limit
        if "speed_limit" in data and data["speed_limit"]["value"] is not None:
            research.speed_limit = int(data["speed_limit"]["value"])
            print(f"[✓] Speed Limit: {research.speed_limit} MPH ({data['speed_limit']['confidence']} confidence)")
        else:
            print(f"[!] Speed Limit: Not found")
        
        # Competitors
        if "competitors" in data:
            research.competitors_count = int(data["competitors"]["count"])
            research.competitors_list = data["competitors"].get("list", [])
            print(f"[✓] Competitors: {research.competitors_count} found within 1 mile ({data['competitors']['confidence']} confidence)")
            for comp in research.competitors_list:
                print(f"    - {comp}")
        else:
            research.competitors_count = 0
            print(f"[!] Competitors: Not found")
        
        # Multifamily Adjacent
        if "multifamily_adjacent" in data:
            research.multifamily_adjacent = data["multifamily_adjacent"]["value"]
            status = "YES" if research.multifamily_adjacent else "NO"
            print(f"[✓] Multifamily Adjacent: {status} ({data['multifamily_adjacent']['confidence']} confidence)")
        else:
            research.multifamily_adjacent = False
            print(f"[!] Multifamily Adjacent: Not determined")
        
        # Retail Adjacent
        if "retail_adjacent" in data:
            research.retail_adjacent = data["retail_adjacent"]["value"]
            status = "YES" if research.retail_adjacent else "NO"
            print(f"[✓] Retail Adjacent: {status} ({data['retail_adjacent']['confidence']} confidence)")
        else:
            research.retail_adjacent = False
            print(f"[!] Retail Adjacent: Not determined")
        
        # Going Home Side
        if "going_home_side" in data:
            research.going_home_side = data["going_home_side"]["value"]
            status = "YES" if research.going_home_side else "NO"
            print(f"[✓] Going Home Side: {status} ({data['going_home_side']['confidence']} confidence)")
            if "explanation" in data["going_home_side"]:
                print(f"    Explanation: {data['going_home_side']['explanation']}")
        else:
            research.going_home_side = False
            print(f"[!] Going Home Side: Not determined")
        
        print()
        return research
        
    except json.JSONDecodeError as e:
        print(f"[✗] Failed to parse JSON response: {e}")
        print(f"[!] Raw response:\n{response_text}\n")
        return research
    except Exception as e:
        print(f"[✗] Error parsing response: {e}")
        return research


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python claude_research.py '<address>'")
        print("Example: python claude_research.py '123 Main St, Orlando, FL 32801'")
        sys.exit(1)
    
    address = sys.argv[1]
    
    print("Car Wash Site Research via Claude API")
    print("=" * 60)
    
    try:
        research = research_site_with_claude(address)
        
        print("\n" + "=" * 60)
        print("RESEARCH SUMMARY")
        print("=" * 60)
        print(f"Address: {address}")
        print(f"Population: {research.population:,}" if research.population else "Population: Unknown")
        print(f"Median Income: ${research.median_income:,}" if research.median_income else "Median Income: Unknown")
        print(f"AADT: {research.aadt:,}" if research.aadt else "AADT: Unknown")
        print(f"Speed Limit: {research.speed_limit} MPH" if research.speed_limit else "Speed Limit: Unknown")
        print(f"Competitors: {research.competitors_count}")
        print(f"Multifamily Adjacent: {'Yes' if research.multifamily_adjacent else 'No'}")
        print(f"Retail Adjacent: {'Yes' if research.retail_adjacent else 'No'}")
        print(f"Going Home Side: {'Yes' if research.going_home_side else 'No'}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
