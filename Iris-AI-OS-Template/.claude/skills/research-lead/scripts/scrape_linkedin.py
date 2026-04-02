"""
Employee: LinkedIn Profile Scraper
Purpose: Scrapes LinkedIn profile data and recent posts using Relevance AI API

Usage:
    python scripts/scrape_linkedin.py "https://www.linkedin.com/in/username/"

Dependencies:
    - requests
    - python-dotenv

Environment Variables:
    - RELEVANCE_AI_PROJECT_ID
    - RELEVANCE_AI_API_KEY

Output:
    JSON object containing:
    - linkedin_profile_details_data: Full profile information
    - last_30_days_posts_transformed: Recent posts from last 30 days
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def scrape_linkedin_profile(linkedin_url, days=30):
    """
    Scrape LinkedIn profile using Relevance AI API

    Args:
        linkedin_url (str): Full LinkedIn profile URL
        days (int): Number of days of posts to fetch (default: 30)

    Returns:
        dict: Profile data and recent posts
    """
    project_id = os.getenv('RELEVANCE_AI_PROJECT_ID')
    api_key = os.getenv('RELEVANCE_AI_API_KEY')

    if not project_id or not api_key:
        raise ValueError("Missing RELEVANCE_AI_PROJECT_ID or RELEVANCE_AI_API_KEY in .env")

    # API endpoint
    url = "https://api-bcbe5a.stack.tryrelevance.com/latest/studios/11cd2604-a05e-444b-a529-0dd300019f97/trigger_webhook"

    # Headers
    headers = {
        "Authorization": f"{project_id}:{api_key}",
        "Content-Type": "application/json"
    }

    # Payload
    payload = {
        "linkedin_url": linkedin_url,
        "last_x_days": days
    }

    # Make request
    try:
        response = requests.post(
            f"{url}?project={project_id}",
            headers=headers,
            json=payload,
            timeout=60  # LinkedIn scraping can take time
        )
        response.raise_for_status()

        data = response.json()

        # Validate response has expected fields
        if 'linkedin_profile_details_data' not in data:
            raise ValueError("Invalid response from Relevance AI - missing profile data")

        # Check if profile data is None or empty
        profile_data = data.get('linkedin_profile_details_data')
        if profile_data is None:
            raise ValueError("Relevance AI returned None for profile data - profile may be private or API limit reached")

        return {
            "success": True,
            "linkedin_profile_details_data": profile_data,
            "last_30_days_posts_transformed": data.get('last_30_days_posts_transformed', ''),
            "raw_response": data
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout - LinkedIn scraping took too long",
            "linkedin_url": linkedin_url
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return {
                "success": False,
                "error": "Rate limit exceeded - wait 60 seconds and retry",
                "status_code": 429,
                "linkedin_url": linkedin_url
            }
        else:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code} - {e.response.text}",
                "status_code": e.response.status_code,
                "linkedin_url": linkedin_url
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "linkedin_url": linkedin_url
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape_linkedin.py <linkedin_url>")
        print("Example: python scripts/scrape_linkedin.py 'https://www.linkedin.com/in/username/'")
        sys.exit(1)

    linkedin_url = sys.argv[1]

    # Optional: days parameter
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    print(f"Scraping LinkedIn profile: {linkedin_url}")
    print(f"Fetching posts from last {days} days...")

    result = scrape_linkedin_profile(linkedin_url, days)

    if result['success']:
        print(f"\n✓ Successfully scraped profile")
        profile = result.get('linkedin_profile_details_data') or {}
        print(f"  Name: {profile.get('full_name', 'Unknown')}")
        print(f"  Company: {profile.get('company', 'Unknown')}")
        print(f"  Role: {profile.get('experiences', [{}])[0].get('title', 'Unknown')}")
    else:
        print(f"\n✗ Scraping failed: {result['error']}")
        sys.exit(1)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
