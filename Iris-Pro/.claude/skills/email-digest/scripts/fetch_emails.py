#!/usr/bin/env python3
import json
import argparse
import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.oauthlib.flow import InstalledAppFlow
import base64
from email.mime.text import MIMEText

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Authenticate with Gmail API."""
    creds = None

    # Try to load user credentials first
    if os.path.exists('token.json'):
        creds = UserCredentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use service account if available, otherwise interactive auth
            try:
                creds = Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=SCOPES
                )
            except:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

        # Save credentials for next time
        if isinstance(creds, UserCredentials):
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    return build('gmail', 'v1', credentials=creds)

def fetch_emails(hours=24, unread_only=False, label='INBOX'):
    """Fetch emails from Gmail."""
    service = get_gmail_service()

    # Build query
    query_parts = []
    if unread_only:
        query_parts.append('is:unread')

    # Time filter
    time_threshold = datetime.now() - timedelta(hours=hours)
    query_parts.append(f'after:{int(time_threshold.timestamp())}')

    query = ' '.join(query_parts) if query_parts else None

    try:
        # Get messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_data['payload']['headers']

            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            to = next((h['value'] for h in headers if h['name'] == 'To'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            # Get body
            body = ''
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                if 'body' in msg_data['payload']:
                    data = msg_data['payload']['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')

            emails.append({
                'id': msg['id'],
                'threadId': msg_data.get('threadId'),
                'subject': subject,
                'sender': sender,
                'to': to,
                'date': date,
                'body': body[:500],  # First 500 chars
                'snippet': msg_data.get('snippet', ''),
                'labels': msg_data.get('labelIds', [])
            })

        return emails

    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    parser.add_argument('--unread-only', action='store_true', help='Only unread emails')
    parser.add_argument('--label', default='INBOX', help='Label to fetch from')
    args = parser.parse_args()

    emails = fetch_emails(args.hours, args.unread_only, args.label)
    print(json.dumps(emails, indent=2))
