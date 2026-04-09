#!/usr/bin/env python3
import json
import argparse
import os
from anthropic import Anthropic

client = Anthropic()

def analyze_emails(emails_json_path):
    """Analyze emails using Claude API."""
    with open(emails_json_path, 'r') as f:
        emails = json.load(f)

    analyzed = []

    for email in emails:
        # Build email summary for Claude
        email_text = f"""
Subject: {email['subject']}
From: {email['sender']}
Date: {email['date']}
Body: {email['body']}
"""

        # Use Claude to analyze
        prompt = f"""Analyze this email and provide:
1. Category: urgent / respond / delegate / archive / irate
2. Sentiment: positive / neutral / negative / irate
3. Urgency: high / medium / low
4. Summary: 1-sentence summary
5. Recommendation: What to do and why

Email:
{email_text}

Respond in JSON format with keys: category, sentiment, urgency, summary, recommendation"""

        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        analysis_text = response.content[0].text

        # Parse Claude's response
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    "category": "respond",
                    "sentiment": "neutral",
                    "urgency": "medium",
                    "summary": email['snippet'],
                    "recommendation": "Review and respond"
                }
        except:
            analysis = {
                "category": "respond",
                "sentiment": "neutral",
                "urgency": "medium",
                "summary": email['snippet'],
                "recommendation": "Review and respond"
            }

        analyzed.append({
            **email,
            **analysis
        })

    return analyzed

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input JSON file with emails')
    args = parser.parse_args()

    analyzed = analyze_emails(args.input)
    print(json.dumps(analyzed, indent=2))
