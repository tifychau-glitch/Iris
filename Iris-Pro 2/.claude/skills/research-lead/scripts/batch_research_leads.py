#!/usr/bin/env python3
"""
Employee: Batch Lead Research Processor
Purpose: Automated daily batch processing of unanalyzed leads from Airtable

This script:
1. Reads Airtable for leads where Status = "Not Analyzed"
2. Processes up to 25 leads per run
3. Runs each lead through the full research pipeline
4. Posts each lead to Slack for review/approval
5. Updates Airtable status to "Awaiting Review"
6. Logs everything to logs/ folder

Usage:
    python .claude/skills/research-lead/scripts/batch_research_leads.py [--limit N] [--dry-run]

Options:
    --limit N    : Maximum number of leads to process (default: 25)
    --dry-run    : Show what would be processed without actually processing

Schedule with cron (8am EST, weekdays only):
    0 8 * * 1-5 cd /path/to/project && python3 .claude/skills/research-lead/scripts/batch_research_leads.py >> logs/cron.log 2>&1

Dependencies:
    - All research_lead.py dependencies
    - Airtable API access
    - Slack API access

Environment Variables:
    - All research_lead.py environment variables
    - AIRTABLE_PERSONAL_ACCESS_TOKEN
    - AIRTABLE_BASE_ID
    - SLACK_BOT_TOKEN

Output:
    Summary of batch processing results
"""

import os
import sys
import json
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

# Paths — skill-relative (scripts/ -> skill root -> project root)
SKILL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = SKILL_ROOT.parent.parent.parent  # research-lead -> skills -> .claude -> project root
SCRIPTS_DIR = SKILL_ROOT / 'scripts'
LOGS_DIR = PROJECT_ROOT / 'logs'
RESEARCH_SCRIPT = SCRIPTS_DIR / 'research_lead.py'


def setup_logging():
    """Set up logging to file and console"""
    LOGS_DIR.mkdir(exist_ok=True)

    # Create log filename with today's date
    log_file = LOGS_DIR / f"batch_research_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def get_unanalyzed_leads(limit=25):
    """Get unanalyzed leads from Airtable"""
    logger = logging.getLogger(__name__)

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / 'airtable_client.py'),
        '--action', 'get-unanalyzed',
        '--limit', str(limit)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to get leads: {result.stderr}")
            return []

        # Parse JSON from output
        data = json.loads(result.stdout)

        if not data.get('success'):
            logger.error(f"airtable_client failed: {data.get('error')}")
            return []

        return data.get('leads', [])

    except Exception as e:
        logger.error(f"Error getting unanalyzed leads: {e}")
        return []


def research_single_lead(linkedin_url, record_id=None):
    """
    Research a single lead using research_lead.py with Slack posting

    Args:
        linkedin_url (str): LinkedIn profile URL
        record_id (str): Airtable record ID (optional)

    Returns:
        dict: Result with success status
    """
    logger = logging.getLogger(__name__)

    logger.info(f"  Starting research: {linkedin_url}")

    cmd = [
        sys.executable,
        str(RESEARCH_SCRIPT),
        linkedin_url,
        '--post-to-slack'  # Always post to Slack in batch mode
    ]

    try:
        # Run research with 10 minute timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            logger.error(f"  ✗ Research failed with code {result.returncode}")
            logger.error(f"  Error: {result.stderr[-500:]}")  # Last 500 chars
            return {
                "success": False,
                "error": f"Research script failed: {result.stderr[-200:]}"
            }

        logger.info(f"  ✓ Research completed successfully")
        return {
            "success": True,
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        logger.error(f"  ✗ Research timed out after 10 minutes")
        return {
            "success": False,
            "error": "Research timed out"
        }
    except Exception as e:
        logger.error(f"  ✗ Research error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Note: Airtable status updates are handled automatically by research_lead.py
# No need for separate update_analyzed_status function


def batch_process_leads(limit=25, dry_run=False):
    """
    Main batch processing function

    Args:
        limit (int): Maximum number of leads to process
        dry_run (bool): If True, only show what would be processed

    Returns:
        dict: Summary of results
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("BATCH LEAD RESEARCH PROCESSOR (Airtable + Slack)")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Limit: {limit} leads")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("")

    # Get unanalyzed leads from Airtable
    logger.info(f"[1/3] Fetching unanalyzed leads from Airtable...")
    leads = get_unanalyzed_leads(limit=limit)

    if not leads:
        logger.info("  No unanalyzed leads found in Airtable")
        return {
            "success": True,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "message": "No leads to process"
        }

    logger.info(f"  Found {len(leads)} unanalyzed lead(s)")

    if dry_run:
        logger.info("\n[DRY RUN] Would process the following leads:")
        for i, lead in enumerate(leads, 1):
            logger.info(f"  {i}. {lead.get('first_name', '')} {lead.get('last_name', '')} @ {lead.get('company', '')}")
            logger.info(f"      LinkedIn: {lead['linkedin_url']}")
        return {
            "success": True,
            "dry_run": True,
            "would_process": len(leads)
        }

    # Process leads
    logger.info(f"\n[2/3] Processing leads and posting to Slack (sequential with 30s delays)...")

    results = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "leads": []
    }

    for i, lead in enumerate(leads, 1):
        record_id = lead.get('record_id')
        linkedin_url = lead['linkedin_url']
        first_name = lead.get('first_name', '')
        last_name = lead.get('last_name', '')
        company = lead.get('company', '')

        logger.info(f"\n--- Lead {i}/{len(leads)}: {first_name} {last_name} @ {company} ---")

        # Research the lead (includes Slack posting)
        research_result = research_single_lead(linkedin_url, record_id)

        lead_summary = {
            "record_id": record_id,
            "linkedin_url": linkedin_url,
            "name": f"{first_name} {last_name}",
            "company": company,
            "success": research_result['success']
        }

        if research_result['success']:
            # Research succeeded and posted to Slack
            # Airtable status automatically updated to "Awaiting Review"
            results['successful'] += 1
            results['processed'] += 1
            logger.info(f"  ✓ Research completed and posted to Slack")

        else:
            # Research failed - STOP processing
            results['failed'] += 1
            results['processed'] += 1
            lead_summary['error'] = research_result.get('error')
            results['leads'].append(lead_summary)

            logger.error("\n" + "=" * 80)
            logger.error("BATCH STOPPED - Research failed for lead")
            logger.error("=" * 80)
            logger.error(f"Failed lead: {first_name} {last_name} @ {company}")
            logger.error(f"LinkedIn: {linkedin_url}")
            logger.error(f"Error: {research_result.get('error')}")
            logger.error("\nAirtable status remains 'Not Analyzed' for failed lead")
            logger.error("Fix the issue and re-run to continue from this lead")

            results['stopped_early'] = True
            results['success'] = False
            return results

        results['leads'].append(lead_summary)

        # Delay before next lead (except for last one)
        if i < len(leads):
            logger.info(f"  ⏳ Waiting 30 seconds before next lead...")
            time.sleep(30)

    # Summary
    logger.info("\n[3/3] Batch processing complete")
    logger.info("=" * 80)
    logger.info("BATCH SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total processed: {results['processed']}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info("")
    logger.info(f"✅ All leads posted to Slack channel 'lead-review'")
    logger.info(f"👉 Review leads in Slack and click Approve/Reject buttons")
    logger.info(f"📊 Check Airtable for lead details and status")
    logger.info("=" * 80)

    results['success'] = True
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Batch process unanalyzed leads from Airtable and post to Slack'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=25,
        help='Maximum number of leads to process (default: 25)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging()

    # Run batch processing
    try:
        result = batch_process_leads(limit=args.limit, dry_run=args.dry_run)

        # Output JSON summary
        print("\n" + json.dumps(result, indent=2))

        # Exit code
        if result.get('success'):
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.error("\n\nBatch processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
