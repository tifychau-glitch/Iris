"""
Employee: Google Sheets Updater
Purpose: Updates Google Sheets with lead research data

Usage:
    python scripts/update_google_sheet.py --linkedin-url "url" --data results.json

Dependencies:
    - google-auth
    - google-auth-oauthlib
    - google-auth-httplib2
    - google-api-python-client
    - python-dotenv

Environment Variables:
    - GOOGLE_SHEETS_CREDENTIALS_FILE (path to credentials.json)
    - GOOGLE_SHEETS_TOKEN_FILE (path to token.json)
    - GOOGLE_SHEETS_DOCUMENT_ID

Output:
    Confirmation of successful update
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("ERROR: Google API libraries not installed.")
    print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

load_dotenv()

# Scopes for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_google_sheets_service():
    """Authenticate and return Google Sheets service"""
    creds = None
    credentials_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
    token_file = os.getenv('GOOGLE_SHEETS_TOKEN_FILE', 'token.json')

    # Check if token file exists
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_file}\n"
                    "Get credentials from: https://console.cloud.google.com/apis/credentials"
                )

            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('sheets', 'v4', credentials=creds)


def find_row_by_linkedin_url(service, spreadsheet_id, sheet_name, linkedin_url):
    """Find row number containing the LinkedIn URL"""
    try:
        # Read all data from sheet
        range_name = f"{sheet_name}!A:Z"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        rows = result.get('values', [])

        if not rows:
            return None

        # Find header row to locate "LinkedIn URL" column
        headers = rows[0]

        try:
            linkedin_col_index = headers.index('LinkedIn URL')
        except ValueError:
            raise ValueError("Column 'LinkedIn URL' not found in sheet headers")

        # Search for matching LinkedIn URL
        for i, row in enumerate(rows[1:], start=2):  # Start at row 2 (skip header)
            if len(row) > linkedin_col_index and row[linkedin_col_index] == linkedin_url:
                return i

        return None

    except HttpError as e:
        raise Exception(f"Error reading sheet: {e}")


def update_google_sheet(linkedin_url, data):
    """
    Update Google Sheets with research data

    Args:
        linkedin_url (str): LinkedIn URL (used as matching key)
        data (dict): Research data to upload

    Returns:
        dict: Update result
    """
    document_id = os.getenv('GOOGLE_SHEETS_DOCUMENT_ID')

    if not document_id:
        raise ValueError("Missing GOOGLE_SHEETS_DOCUMENT_ID in .env")

    try:
        service = get_google_sheets_service()

        # Get spreadsheet info
        spreadsheet = service.spreadsheets().get(spreadsheetId=document_id).execute()
        sheets = spreadsheet.get('sheets', [])

        if not sheets:
            raise ValueError("No sheets found in document")

        # Use first sheet
        sheet_name = sheets[0]['properties']['title']
        sheet_id = sheets[0]['properties']['sheetId']

        # Find row with this LinkedIn URL
        row_number = find_row_by_linkedin_url(service, document_id, sheet_name, linkedin_url)

        # Extract profile data
        profile = data.get('profile_data', {})
        experiences = profile.get('experiences', [])
        position = experiences[0].get('title', '') if experiences else ''

        # Extract research data
        lead_profile = data.get('lead_profile', {}).get('data', {})
        pain_gain = data.get('pain_gain_operational', {}).get('data', {})
        # Archetype is stored in dm_sequence.data, not pain_gain
        dm_data = data.get('dm_sequence', {}).get('data', {})
        archetype = dm_data.get('archetype', '')

        # Extract quality data (handle None when quality reviewer disabled)
        quality_review_result = data.get('dm_quality_review') or {}
        quality_review = quality_review_result.get('data', {})
        quality_score = quality_review.get('overall_quality_score', 'N/A') if quality_review else 'N/A'
        quality_flags = data.get('quality_flags', [])
        requires_manual_review = data.get('requires_manual_review', False)
        review_report_path = data.get('review_report_path', '')

        # Prepare update data - STANDARDIZED HEADERS (matches Airtable format)
        update_values = {
            # Core profile fields
            "LinkedIn URL": linkedin_url,
            "First Name": profile.get('first_name', ''),
            "Last Name": profile.get('last_name', ''),
            "Company": profile.get('company', ''),
            "Position": position,
            "Location": profile.get('location', profile.get('city', '')),
            "Email": profile.get('email', ''),

            # Research data
            "Archetype": archetype,

            # Messaging (renamed from Email#1/2/3 Body to match Airtable)
            "DM 1": data.get('dm_sequence', {}).get('data', {}).get('dm1', {}).get('message', ''),
            "DM 2": data.get('dm_sequence', {}).get('data', {}).get('dm2', {}).get('message', ''),
            "DM 3": data.get('dm_sequence', {}).get('data', {}).get('dm3', {}).get('message', ''),
            "Connection Request": data.get('connection_request', {}).get('data', {}).get('connection_request', ''),

            # Quality & review
            "Quality Score": str(quality_score),
            "Quality Flags": ', '.join(quality_flags) if quality_flags else 'None',
            "Status": "Rejected" if requires_manual_review else "Awaiting Review",
            "Review Report URL": review_report_path,

            # System fields
            "Analysed": "Yes"
        }

        # Get headers
        headers_result = service.spreadsheets().values().get(
            spreadsheetId=document_id,
            range=f"{sheet_name}!1:1"
        ).execute()

        headers = headers_result.get('values', [[]])[0]

        # Map values to columns
        update_data = []
        for header in headers:
            if header in update_values:
                value = update_values[header]
                # Convert dicts to JSON strings
                if isinstance(value, dict):
                    value = json.dumps(value, indent=2)
                update_data.append(value)
            else:
                update_data.append('')  # Keep existing value

        if row_number:
            # Update existing row
            range_name = f"{sheet_name}!A{row_number}:Z{row_number}"

            service.spreadsheets().values().update(
                spreadsheetId=document_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [update_data]}
            ).execute()

            return {
                "success": True,
                "action": "updated",
                "row": row_number,
                "linkedin_url": linkedin_url
            }
        else:
            # Append new row
            range_name = f"{sheet_name}!A:Z"

            service.spreadsheets().values().append(
                spreadsheetId=document_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [update_data]}
            ).execute()

            return {
                "success": True,
                "action": "appended",
                "linkedin_url": linkedin_url
            }

    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Update Google Sheets with lead research')
    parser.add_argument('--linkedin-url', required=True, help='LinkedIn URL')
    parser.add_argument('--data', required=True, help='Path to JSON data file')

    args = parser.parse_args()

    # Load data
    try:
        with open(args.data, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Failed to load data file: {e}")
        sys.exit(1)

    print(f"Updating Google Sheets for: {args.linkedin_url}")

    result = update_google_sheet(args.linkedin_url, data)

    if result['success']:
        print(f"✓ Sheet {result['action']} successfully")
        if result.get('row'):
            print(f"  Row: {result['row']}")
    else:
        print(f"✗ Update failed: {result['error']}")
        sys.exit(1)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
