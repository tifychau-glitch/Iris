"""
Employee: Airtable Client
Purpose: CRUD operations for Lead Research Airtable base

Usage:
    python scripts/airtable_client.py --action create-lead --data results.json
    python scripts/airtable_client.py --action update-lead --linkedin-url "https://..." --data results.json
    python scripts/airtable_client.py --action get-lead --linkedin-url "https://..."
    python scripts/airtable_client.py --action get-unanalyzed --limit 25
    python scripts/airtable_client.py --action mark-approved --linkedin-url "https://..." --campaign-id 279043
    python scripts/airtable_client.py --action mark-rejected --linkedin-url "https://..." --reason "Not ICP fit"
    python scripts/airtable_client.py --action mark-sent --linkedin-url "https://..." --campaign-id 279043

Dependencies:
    - requests
    - python-dotenv

Environment Variables:
    - AIRTABLE_PERSONAL_ACCESS_TOKEN
    - AIRTABLE_BASE_ID
    - AIRTABLE_TABLE_NAME

Output:
    JSON object with operation results
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Airtable configuration
AIRTABLE_TOKEN = os.getenv('AIRTABLE_PERSONAL_ACCESS_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME', 'Leads')

# Airtable API endpoint
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"


def get_headers():
    """Get headers for Airtable API requests"""
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }


def find_lead_by_linkedin_url(linkedin_url):
    """
    Find a lead record by LinkedIn URL

    Args:
        linkedin_url (str): LinkedIn profile URL

    Returns:
        dict: Record if found, None otherwise
    """
    # URL encode the formula
    formula = f"{{LinkedIn URL}}='{linkedin_url}'"

    params = {
        "filterByFormula": formula,
        "maxRecords": 1
    }

    try:
        response = requests.get(
            AIRTABLE_API_URL,
            headers=get_headers(),
            params=params,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        records = data.get('records', [])

        if records:
            return records[0]
        return None

    except Exception as e:
        print(f"Error finding lead: {e}", file=sys.stderr)
        return None


def map_research_to_airtable_fields(research_data):
    """
    Map research results to Airtable field structure

    Args:
        research_data (dict): Research results from research_lead.py

    Returns:
        dict: Airtable fields object
    """
    profile = research_data.get('profile_data', {})
    lead_profile = research_data.get('lead_profile', {}).get('data', {})
    connection_req = research_data.get('connection_request', {}).get('data', {})
    dm_sequence = research_data.get('dm_sequence', {}).get('data', {})
    # Handle dm_quality_review = None (when quality reviewer is disabled)
    quality_review_result = research_data.get('dm_quality_review') or {}
    quality_review = quality_review_result.get('data', {})
    quality_flags = research_data.get('quality_flags', [])

    # Get position from experiences
    position = ''
    experiences = profile.get('experiences', [])
    if experiences and len(experiences) > 0:
        position = experiences[0].get('title', '')

    # Build fields object with core fields only (expandable later)
    # Start with minimal required fields that should exist in most Airtable setups
    core_fields = {
        "LinkedIn URL": research_data.get('linkedin_url', profile.get('linkedin_url', '')),
        "Status": "Awaiting Review",
        "First Name": profile.get('first_name', ''),
        "Last Name": profile.get('last_name', ''),
        "Company": profile.get('company', ''),
    }

    # Optional fields - only include if they have values
    # NOTE: Connection Request removed - now handled via HeyReach template
    optional_fields = {
        "Position": position,
        "Location": profile.get('location', profile.get('city', '')),
        "Email": profile.get('email', ''),
        "Quality Score": quality_review.get('overall_quality_score', 0),
        "DM 1": dm_sequence.get('dm1', {}).get('message', ''),
        "DM 2": dm_sequence.get('dm2', {}).get('message', ''),
        "DM 3": dm_sequence.get('dm3', {}).get('message', ''),
    }

    # Merge core and optional, removing empty values
    fields = {**core_fields}
    for key, value in optional_fields.items():
        if value not in [None, '', 0]:
            fields[key] = value

    return fields


def create_lead(research_data):
    """
    Create a new lead record in Airtable

    Args:
        research_data (dict): Research results

    Returns:
        dict: Created record
    """
    fields = map_research_to_airtable_fields(research_data)

    payload = {
        "fields": fields
    }

    try:
        response = requests.post(
            AIRTABLE_API_URL,
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        record = response.json()

        return {
            "success": True,
            "action": "created",
            "record_id": record.get('id'),
            "linkedin_url": fields.get("LinkedIn URL"),
            "status": fields.get("Status")
        }

    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error: {e.response.status_code} - {e.response.text}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def update_lead(linkedin_url, research_data):
    """
    Update an existing lead record (or create if not exists)

    Args:
        linkedin_url (str): LinkedIn profile URL
        research_data (dict): Research results

    Returns:
        dict: Update result
    """
    # Find existing record
    existing_record = find_lead_by_linkedin_url(linkedin_url)

    fields = map_research_to_airtable_fields(research_data)

    if existing_record:
        # Update existing record
        record_id = existing_record['id']
        url = f"{AIRTABLE_API_URL}/{record_id}"

        payload = {
            "fields": fields
        }

        try:
            response = requests.patch(
                url,
                headers=get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            return {
                "success": True,
                "action": "updated",
                "record_id": record_id,
                "linkedin_url": linkedin_url,
                "status": fields.get("Status")
            }

        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code} - {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    else:
        # Create new record
        return create_lead(research_data)


def get_lead(linkedin_url):
    """
    Get a lead record by LinkedIn URL

    Args:
        linkedin_url (str): LinkedIn profile URL

    Returns:
        dict: Lead record or error
    """
    record = find_lead_by_linkedin_url(linkedin_url)

    if record:
        return {
            "success": True,
            "record": record
        }
    else:
        return {
            "success": False,
            "error": "Lead not found"
        }


def get_unanalyzed_leads(limit=25):
    """
    Get leads with Status = "Not Analyzed"

    Args:
        limit (int): Max number of leads to return

    Returns:
        dict: List of unanalyzed leads
    """
    formula = "{Status}='Not Analyzed'"

    params = {
        "filterByFormula": formula,
        "maxRecords": limit,
        "sort[0][field]": "Created Time",
        "sort[0][direction]": "asc"
    }

    try:
        response = requests.get(
            AIRTABLE_API_URL,
            headers=get_headers(),
            params=params,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        records = data.get('records', [])

        # Format records for easy consumption
        leads = []
        for record in records:
            fields = record.get('fields', {})
            leads.append({
                "record_id": record.get('id'),
                "linkedin_url": fields.get('LinkedIn URL'),
                "first_name": fields.get('First Name', ''),
                "last_name": fields.get('Last Name', ''),
                "company": fields.get('Company', '')
            })

        return {
            "success": True,
            "count": len(leads),
            "leads": leads
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def mark_approved(linkedin_url, campaign_id, campaign_name=None):
    """
    Mark a lead as approved

    Args:
        linkedin_url (str): LinkedIn profile URL
        campaign_id (int): HeyReach campaign ID
        campaign_name (str): HeyReach campaign name (optional)

    Returns:
        dict: Update result
    """
    record = find_lead_by_linkedin_url(linkedin_url)

    if not record:
        return {
            "success": False,
            "error": "Lead not found"
        }

    record_id = record['id']
    url = f"{AIRTABLE_API_URL}/{record_id}"

    fields = {
        "Status": "Approved",
        "Reviewed Date": datetime.now().strftime('%Y-%m-%d'),
        "HeyReach Campaign ID": campaign_id
    }

    if campaign_name:
        fields["HeyReach Campaign"] = campaign_name

    payload = {"fields": fields}

    try:
        response = requests.patch(
            url,
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        return {
            "success": True,
            "action": "approved",
            "record_id": record_id,
            "linkedin_url": linkedin_url
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def mark_rejected(linkedin_url, reason=None):
    """
    Mark a lead as rejected

    Args:
        linkedin_url (str): LinkedIn profile URL
        reason (str): Rejection reason (optional)

    Returns:
        dict: Update result
    """
    record = find_lead_by_linkedin_url(linkedin_url)

    if not record:
        return {
            "success": False,
            "error": "Lead not found"
        }

    record_id = record['id']
    url = f"{AIRTABLE_API_URL}/{record_id}"

    fields = {
        "Status": "Rejected",
        "Reviewed Date": datetime.now().strftime('%Y-%m-%d')
    }

    if reason:
        fields["Rejection Reason"] = reason

    payload = {"fields": fields}

    try:
        response = requests.patch(
            url,
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        return {
            "success": True,
            "action": "rejected",
            "record_id": record_id,
            "linkedin_url": linkedin_url
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def mark_sent(linkedin_url, campaign_id, campaign_name=None):
    """
    Mark a lead as sent to HeyReach

    Args:
        linkedin_url (str): LinkedIn profile URL
        campaign_id (int): HeyReach campaign ID
        campaign_name (str): HeyReach campaign name (optional)

    Returns:
        dict: Update result
    """
    record = find_lead_by_linkedin_url(linkedin_url)

    if not record:
        return {
            "success": False,
            "error": "Lead not found"
        }

    record_id = record['id']
    url = f"{AIRTABLE_API_URL}/{record_id}"

    fields = {
        "Status": "Sent to HeyReach",
        "Sent to HeyReach": True,
        "Sent Date": datetime.now().strftime('%Y-%m-%d'),
        "HeyReach Campaign ID": campaign_id
    }

    if campaign_name:
        fields["HeyReach Campaign"] = campaign_name

    payload = {"fields": fields}

    try:
        response = requests.patch(
            url,
            headers=get_headers(),
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        return {
            "success": True,
            "action": "sent",
            "record_id": record_id,
            "linkedin_url": linkedin_url
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Airtable Lead Database Client')
    parser.add_argument('--action', required=True,
                        choices=['create-lead', 'update-lead', 'get-lead', 'get-unanalyzed',
                                'mark-approved', 'mark-rejected', 'mark-sent'],
                        help='Action to perform')
    parser.add_argument('--linkedin-url', help='LinkedIn profile URL')
    parser.add_argument('--data', help='Path to research results JSON')
    parser.add_argument('--limit', type=int, default=25, help='Limit for get-unanalyzed')
    parser.add_argument('--campaign-id', type=int, help='HeyReach campaign ID')
    parser.add_argument('--campaign-name', help='HeyReach campaign name')
    parser.add_argument('--reason', help='Rejection reason')

    args = parser.parse_args()

    # Validate environment
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        print(json.dumps({
            "success": False,
            "error": "Missing AIRTABLE_PERSONAL_ACCESS_TOKEN or AIRTABLE_BASE_ID in .env"
        }))
        sys.exit(1)

    result = None

    if args.action == 'create-lead':
        if not args.data:
            print(json.dumps({"success": False, "error": "--data required for create-lead"}))
            sys.exit(1)

        with open(args.data, 'r') as f:
            research_data = json.load(f)

        result = create_lead(research_data)

    elif args.action == 'update-lead':
        if not args.linkedin_url or not args.data:
            print(json.dumps({"success": False, "error": "--linkedin-url and --data required"}))
            sys.exit(1)

        with open(args.data, 'r') as f:
            research_data = json.load(f)

        result = update_lead(args.linkedin_url, research_data)

    elif args.action == 'get-lead':
        if not args.linkedin_url:
            print(json.dumps({"success": False, "error": "--linkedin-url required"}))
            sys.exit(1)

        result = get_lead(args.linkedin_url)

    elif args.action == 'get-unanalyzed':
        result = get_unanalyzed_leads(args.limit)

    elif args.action == 'mark-approved':
        if not args.linkedin_url or not args.campaign_id:
            print(json.dumps({"success": False, "error": "--linkedin-url and --campaign-id required"}))
            sys.exit(1)

        result = mark_approved(args.linkedin_url, args.campaign_id, args.campaign_name)

    elif args.action == 'mark-rejected':
        if not args.linkedin_url:
            print(json.dumps({"success": False, "error": "--linkedin-url required"}))
            sys.exit(1)

        result = mark_rejected(args.linkedin_url, args.reason)

    elif args.action == 'mark-sent':
        if not args.linkedin_url or not args.campaign_id:
            print(json.dumps({"success": False, "error": "--linkedin-url and --campaign-id required"}))
            sys.exit(1)

        result = mark_sent(args.linkedin_url, args.campaign_id, args.campaign_name)

    # Output result
    print(json.dumps(result, indent=2))

    if not result.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    main()
