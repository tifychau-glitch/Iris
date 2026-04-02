"""
Employee: Post Lead Review to Slack
Purpose: Post lead review cards to Slack with approve/reject buttons

Usage:
    python scripts/post_lead_review_to_slack.py --data results.json --channel lead-review
    python scripts/post_lead_review_to_slack.py --data results.json --channel lead-review --thread-ts 1702389600.123456

Dependencies:
    - slack_sdk
    - python-dotenv

Environment Variables:
    - SLACK_LEAD_REVIEW_BOT_TOKEN (or SLACK_BOT_TOKEN)
    - SLACK_LEAD_REVIEW_CHANNEL
    - AIRTABLE_BASE_ID

Output:
    JSON with message timestamp and thread info
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

# Slack configuration
SLACK_TOKEN = os.getenv('SLACK_LEAD_REVIEW_BOT_TOKEN') or os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_LEAD_REVIEW_CHANNEL', 'lead-review')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')

# Initialize Slack client
slack_client = WebClient(token=SLACK_TOKEN)


def get_or_create_daily_thread(channel):
    """
    Get today's review thread or create if doesn't exist

    Args:
        channel (str): Slack channel name or ID

    Returns:
        str: Thread timestamp
    """
    today = datetime.now().strftime('%A, %B %d, %Y')
    thread_title = f"📅 Lead Review - {today}"

    try:
        # Try to search for existing thread (requires channels:history permission)
        try:
            result = slack_client.conversations_history(
                channel=channel,
                limit=50
            )

            # Look for today's thread
            for message in result['messages']:
                if message.get('text', '').startswith(f"📅 Lead Review - {today}"):
                    return message['ts']
        except SlackApiError as history_error:
            # If we can't read history (permission missing), just create a new thread
            if history_error.response['error'] == 'channel_not_found':
                print(f"⚠ Cannot read channel history (missing channels:history permission), creating new thread", file=sys.stderr)
            else:
                raise

        # Create new thread (either no thread found or couldn't read history)
        result = slack_client.chat_postMessage(
            channel=channel,
            text=thread_title,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": thread_title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_Leads researched today will appear below. Review and approve to send to HeyReach._"
                    }
                }
            ]
        )

        return result['ts']

    except SlackApiError as e:
        print(f"Error creating thread: {e.response['error']}", file=sys.stderr)
        return None


def build_lead_review_blocks(research_data):
    """
    Build Slack Block Kit blocks for lead review card

    Args:
        research_data (dict): Research results

    Returns:
        list: Slack blocks
    """
    profile = research_data.get('profile_data', {})
    lead_profile = research_data.get('lead_profile', {}).get('data', {})
    # Connection request removed - now handled via HeyReach template
    connection_req = {}
    dm_sequence = research_data.get('dm_sequence', {}).get('data', {})
    quality_review = research_data.get('dm_quality_review', {}).get('data', {})
    quality_flags = research_data.get('quality_flags', [])

    # Extract all available citations from Perplexity data
    def extract_citations(research_data):
        citations = []
        perp = research_data.get('perplexity_data', {})

        # LinkedIn profile
        linkedin_url = research_data.get('linkedin_url', '')
        if linkedin_url:
            citations.append(f"LinkedIn Profile: {linkedin_url}")

        # Company profile
        if perp.get('company_profile', {}).get('source_url'):
            citations.append(f"Company About: {perp['company_profile']['source_url']}")

        # Leader facts
        for fact in perp.get('leader_facts', [])[:2]:
            if fact.get('source_url'):
                citations.append(f"{fact.get('source', 'Source')}: {fact['source_url']}")

        # Growth signals
        for signal in perp.get('growth_signals', [])[:2]:
            if signal.get('source_url'):
                citations.append(f"Growth signal: {signal['source_url']}")

        return citations[:4]  # Max 4 citations

    all_citations = extract_citations(research_data)

    first_name = profile.get('first_name', '')
    last_name = profile.get('last_name', '')
    full_name = profile.get('full_name', f"{first_name} {last_name}")
    company = profile.get('company', 'Unknown Company')
    position = ''
    experiences = profile.get('experiences', [])
    if experiences and len(experiences) > 0:
        position = experiences[0].get('title', '')

    linkedin_url = research_data.get('linkedin_url', profile.get('linkedin_url', ''))
    quality_score = quality_review.get('overall_quality_score', 0)
    approval_rec = quality_review.get('approval_recommendation', 'UNKNOWN')
    archetype = dm_sequence.get('archetype', 'Unknown')

    # Determine quality badge
    if quality_score >= 8:
        quality_badge = f"✅ {quality_score}/10"
        quality_color = "good"
    elif quality_score >= 6:
        quality_badge = f"🟡 {quality_score}/10"
        quality_color = "warning"
    else:
        quality_badge = f"⚠️ {quality_score}/10"
        quality_color = "danger"

    # Build Airtable link
    airtable_link = f"https://airtable.com/{AIRTABLE_BASE_ID}" if AIRTABLE_BASE_ID else None

    blocks = [
        # Header
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 {full_name}"
            }
        },
        # Basic info
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{position}* @ *{company}*\n<{linkedin_url}|View LinkedIn Profile>"
            }
        },
        # Quality score & archetype
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Quality Score:* {quality_badge}  |  *Recommendation:* {approval_rec}\\n*Archetype:* {archetype}"
            }
        }
    ]

    # Quality flags (if any)
    if quality_flags:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⚠️ *Flags:*\n{'  •  '.join(quality_flags)}"
            }
        })

    blocks.append({"type": "divider"})

    # Person profile
    if lead_profile.get('person_profile'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📝 Person Profile*\n{lead_profile['person_profile'][:500]}"
            }
        })

    # Unique facts
    if lead_profile.get('unique_facts'):
        facts_list = lead_profile['unique_facts']
        if isinstance(facts_list, list):
            facts_text = '\n'.join([f"• {fact}" for fact in facts_list])
        else:
            facts_text = facts_list
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🎯 Unique Facts*\n{facts_text}"
            }
        })

    blocks.append({"type": "divider"})

    # Connection Request (now handled via HeyReach template)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*💬 Connection Request*\n_Connection requests handled via HeyReach template (not AI-generated)_"
        }
    })

    # DM 1
    dm1_msg = dm_sequence.get('dm1', {}).get('message', '')
    dm1_chars = dm_sequence.get('dm1', {}).get('character_count', len(dm1_msg))
    dm1_hook = dm_sequence.get('dm1', {}).get('hook_used', '')
    dm1_text = f"*💬 DM 1* ({dm1_chars} chars)\n```{dm1_msg}```\n✓ _Hook: {dm1_hook}_"
    if all_citations:
        citations_text = '\n'.join([f"• {cit}" for cit in all_citations[:3]])
        dm1_text += f"\n_Research sources:_\n{citations_text}"
    else:
        dm1_text += f"\n_⚠️ No research sources - AI used inference_"
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": dm1_text
        }
    })

    # DM 2
    dm2_msg = dm_sequence.get('dm2', {}).get('message', '')
    dm2_chars = dm_sequence.get('dm2', {}).get('character_count', len(dm2_msg))
    dm2_gap = dm_sequence.get('dm2', {}).get('gap_referenced', '')
    dm2_text = f"*💬 DM 2* ({dm2_chars} chars)\n```{dm2_msg}```\n✓ _Gap: {dm2_gap}_"
    if all_citations:
        citations_text = '\n'.join([f"• {cit}" for cit in all_citations[:3]])
        dm2_text += f"\n_Research sources:_\n{citations_text}"
    else:
        dm2_text += f"\n_⚠️ No research sources - AI used inference_"
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": dm2_text
        }
    })

    # DM 3
    dm3_msg = dm_sequence.get('dm3', {}).get('message', '')
    dm3_chars = dm_sequence.get('dm3', {}).get('character_count', len(dm3_msg))
    dm3_text = f"*💬 DM 3* ({dm3_chars} chars)\n```{dm3_msg}```"
    if all_citations:
        citations_text = '\n'.join([f"• {cit}" for cit in all_citations[:3]])
        dm3_text += f"\n_Research sources:_\n{citations_text}"
    else:
        dm3_text += f"\n_⚠️ No research sources - AI used inference_"
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": dm3_text
        }
    })

    blocks.append({"type": "divider"})

    # Action buttons - store linkedin_url in value for webhook handler
    blocks.append({
        "type": "actions",
        "block_id": "lead_approval_actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Approve & Send to HeyReach"
                },
                "style": "primary",
                "action_id": "approve_lead",
                "value": linkedin_url
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "❌ Reject"
                },
                "style": "danger",
                "action_id": "reject_lead",
                "value": linkedin_url
            }
        ]
    })

    # Airtable link (if available)
    if airtable_link:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<{airtable_link}|View in Airtable> | Researched: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            ]
        })

    return blocks


def post_lead_review(research_data, channel, thread_ts=None):
    """
    Post lead review card to Slack

    Args:
        research_data (dict): Research results
        channel (str): Slack channel name or ID
        thread_ts (str): Thread timestamp (optional, will find/create daily thread if not provided)

    Returns:
        dict: Result with message timestamp
    """
    # Get or create daily thread if not provided
    if not thread_ts:
        thread_ts = get_or_create_daily_thread(channel)
        if not thread_ts:
            return {
                "success": False,
                "error": "Failed to create/find daily thread"
            }

    # Build blocks
    blocks = build_lead_review_blocks(research_data)

    # Get lead name for fallback text
    profile = research_data.get('profile_data', {})
    full_name = profile.get('full_name', 'Unknown Lead')

    try:
        # Post message in thread
        result = slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Lead review: {full_name}",  # Fallback text
            blocks=blocks
        )

        return {
            "success": True,
            "channel": result['channel'],
            "ts": result['ts'],
            "thread_ts": thread_ts,
            "linkedin_url": research_data.get('linkedin_url', '')
        }

    except SlackApiError as e:
        return {
            "success": False,
            "error": f"Slack API error: {e.response['error']}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Post lead review card to Slack')
    parser.add_argument('--data', required=True, help='Path to research results JSON')
    parser.add_argument('--channel', help='Slack channel (overrides env var)')
    parser.add_argument('--thread-ts', help='Specific thread timestamp (optional)')

    args = parser.parse_args()

    # Validate Slack token
    if not SLACK_TOKEN:
        print(json.dumps({
            "success": False,
            "error": "Missing SLACK_LEAD_REVIEW_BOT_TOKEN or SLACK_BOT_TOKEN in .env"
        }))
        sys.exit(1)

    # Load research data
    try:
        with open(args.data, 'r') as f:
            research_data = json.load(f)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Failed to load research data: {e}"
        }))
        sys.exit(1)

    # Determine channel
    channel = args.channel or SLACK_CHANNEL

    # Post to Slack
    result = post_lead_review(research_data, channel, args.thread_ts)

    # Output result
    print(json.dumps(result, indent=2))

    if not result.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    main()
