#!/usr/bin/env python3
import json
import argparse
import os
import requests
from datetime import datetime

def send_telegram_digest(analyzed_emails_path, chat_id):
    """Send email digest to Telegram."""
    with open(analyzed_emails_path, 'r') as f:
        analyzed_emails = json.load(f)

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return

    # Build message
    message = f"📧 *Email Digest* — {datetime.now().strftime('%B %d')}\n"
    message += "=" * 40 + "\n\n"

    urgent = [e for e in analyzed_emails if e.get('category') == 'urgent']
    respond = [e for e in analyzed_emails if e.get('category') == 'respond']
    delegate = [e for e in analyzed_emails if e.get('category') == 'delegate']

    if urgent:
        message += f"🔴 *URGENT* ({len(urgent)})\n"
        for email in urgent[:3]:  # Limit to 3 in Telegram
            message += f"  • {email['sender']}\n"
            message += f"    {email['subject'][:40]}...\n"
        if len(urgent) > 3:
            message += f"  +{len(urgent) - 3} more\n"
        message += "\n"

    if respond:
        message += f"🟡 *RESPOND* ({len(respond)})\n"
        for email in respond[:2]:
            message += f"  • {email['sender']}\n"
        if len(respond) > 2:
            message += f"  +{len(respond) - 2} more\n"
        message += "\n"

    if delegate:
        message += f"🟢 *DELEGATE* ({len(delegate)})\n"

    total = len(analyzed_emails)
    message += f"\n_Total: {total} emails_"

    # Send via Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"Telegram digest sent to chat {chat_id}")
        else:
            print(f"Error sending Telegram message: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input JSON file with analyzed emails')
    parser.add_argument('--telegram-chat-id', required=True, help='Telegram chat ID')
    args = parser.parse_args()

    send_telegram_digest(args.input, args.telegram_chat_id)
