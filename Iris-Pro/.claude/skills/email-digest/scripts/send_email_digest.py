#!/usr/bin/env python3
import json
import argparse
import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """Authenticate with Gmail API."""
    creds = None

    if os.path.exists('token.json'):
        creds = UserCredentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                creds = Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=SCOPES
                )
            except:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

        if isinstance(creds, UserCredentials):
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def create_email_body(analyzed_emails):
    """Create plain text email body from analyzed emails."""
    body = "EMAIL DIGEST — " + datetime.now().strftime("%B %d, %Y") + "\n"
    body += "=" * 50 + "\n\n"

    # Organize by category
    urgent = [e for e in analyzed_emails if e.get('category') == 'urgent']
    respond = [e for e in analyzed_emails if e.get('category') == 'respond']
    delegate = [e for e in analyzed_emails if e.get('category') == 'delegate']
    archive = [e for e in analyzed_emails if e.get('category') == 'archive']

    if urgent:
        body += f"URGENT ({len(urgent)})\n"
        body += "-" * 30 + "\n"
        for email in urgent:
            body += f"\nFrom: {email['sender']}\n"
            body += f"Subject: {email['subject']}\n"
            body += f"Urgency: {email.get('urgency', 'N/A')}\n"
            body += f"Recommendation: {email.get('recommendation', 'Review')}\n"
        body += "\n"

    if respond:
        body += f"RESPOND ({len(respond)})\n"
        body += "-" * 30 + "\n"
        for email in respond:
            body += f"\nFrom: {email['sender']}\n"
            body += f"Subject: {email['subject']}\n"
            body += f"Summary: {email.get('summary', email.get('snippet', 'N/A'))}\n"
        body += "\n"

    if delegate:
        body += f"DELEGATE ({len(delegate)})\n"
        body += "-" * 30 + "\n"
        for email in delegate:
            body += f"\nFrom: {email['sender']}\n"
            body += f"Subject: {email['subject']}\n"
        body += "\n"

    if archive:
        body += f"ARCHIVE ({len(archive)})\n"
        body += f"  {len(archive)} emails ready to archive\n\n"

    other = [e for e in analyzed_emails if e.get('category') not in ['urgent', 'respond', 'delegate', 'archive']]
    if other:
        body += f"OTHER ({len(other)})\n"
        body += f"  {len(other)} emails to review\n"

    return body

def send_email(recipient, analyzed_emails_path):
    """Send email digest."""
    service = get_gmail_service()

    with open(analyzed_emails_path, 'r') as f:
        analyzed_emails = json.load(f)

    body = create_email_body(analyzed_emails)

    message = MIMEText(body)
    message['to'] = recipient
    message['subject'] = f"Email Digest — {datetime.now().strftime('%B %d')}"

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    try:
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        print(f"Email digest sent to {recipient}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input JSON file with analyzed emails')
    parser.add_argument('--recipient-email', required=True, help='Email recipient address')
    args = parser.parse_args()

    send_email(args.recipient_email, args.input)
