#!/usr/bin/env python3
"""
Main Orchestration Script: Lead Research & Personalization

This is the orchestrator that coordinates all tool scripts to transform
a LinkedIn URL into a complete research package with personalized outreach.

Usage:
    python .claude/skills/research-lead/scripts/research_lead.py "https://www.linkedin.com/in/username/"

Workflow:
    1. Scrape LinkedIn profile + recent posts
    2. Research company & person (Perplexity)
    3. Run AI analyses in parallel (OpenAI)
    4. Generate review report
    5. Upload results to Google Sheets

See: .claude/skills/research-lead/SKILL.md for full details
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
import concurrent.futures
from pathlib import Path

# Paths — skill-relative (scripts/ -> skill root -> project root)
SCRIPTS_DIR = Path(__file__).parent
SKILL_ROOT = SCRIPTS_DIR.parent
PROJECT_ROOT = SKILL_ROOT.parent.parent.parent  # research-lead -> skills -> .claude -> project root
TMP_DIR = PROJECT_ROOT / '.tmp'


def ensure_tmp_dir():
    """Create .tmp directory if it doesn't exist"""
    TMP_DIR.mkdir(exist_ok=True)


def run_tool(script_name, args, capture_json=True):
    """
    Run a tool script and return the result

    Args:
        script_name (str): Name of the tool script (e.g., 'scrape_linkedin.py')
        args (list): Command-line arguments to pass
        capture_json (bool): Whether to parse JSON from output

    Returns:
        dict: Result from the tool script
    """
    # All scripts live in the same directory (v2 skill structure)
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Only treat non-zero return codes as errors
        # (stderr may contain warnings which are OK)
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Tool failed with code {result.returncode}: {result.stderr}",
                "tool": script_name
            }

        if capture_json:
            # Try to extract JSON from output
            output = result.stdout

            # Find JSON in output (look for first complete { ... })
            # Try multiple strategies
            json_obj = None

            # Strategy 1: Try to find a { and parse from there
            brace_positions = [i for i, c in enumerate(output) if c == '{']
            for start_pos in brace_positions:
                try:
                    json_obj = json.loads(output[start_pos:])
                    break  # Success!
                except json.JSONDecodeError:
                    continue  # Try next brace

            if json_obj:
                return json_obj
            else:
                return {
                    "success": False,
                    "error": "Failed to parse JSON from tool output",
                    "raw_output": output[:1000]  # Limit output for debugging
                }

        return {
            "success": True,
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Tool timed out after 5 minutes",
            "tool": script_name
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool": script_name
        }


def save_temp_json(data, filename):
    """Save data to temporary JSON file"""
    filepath = TMP_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    return str(filepath)


def run_analysis(analysis_type, input_data, model=None, additional_context=None):
    """Run a single OpenAI analysis

    Args:
        analysis_type: Type of analysis to run
        input_data: Input data dict
        model: Optional model override
        additional_context: Optional feedback/context to append to prompt
    """
    print(f"  - Running {analysis_type} analysis...")

    # Save input data to temp file
    input_file = save_temp_json(input_data, f'analysis_input_{analysis_type}.json')

    # Run analysis
    args = ['--type', analysis_type, '--input', input_file]
    if model:
        args.extend(['--model', model])
    if additional_context:
        # Save context to file and pass path
        context_file = save_temp_json({'context': additional_context}, f'context_{analysis_type}.json')
        args.extend(['--additional-context', context_file])

    result = run_tool('analyze_with_openai.py', args)

    return analysis_type, result


def run_dm_sequence_with_quality_loop(analysis_input, profile_data, posts_data, perplexity_data,
                                       lead_profile_content, pain_gain_content, max_retries=2):
    """
    Run dm_sequence (quality review loop commented out - 2024-12-16)

    QUALITY REVIEWER TEMPORARILY DISABLED:
    The quality reviewer was being overly critical and rejecting good DMs due to
    rubric misalignment. It expected hooks from pattern_interrupt_hooks but the
    dm_sequence now correctly prioritizes person-specific unique_facts.

    TODO: Update dm_quality_review rubric to match dm_sequence behavior, then re-enable.
    """
    print(f"  - Running dm_sequence...")

    # Run dm_sequence once (no retry loop)
    _, dm_result = run_analysis('dm_sequence', analysis_input, None, None)

    if not dm_result.get('success'):
        print(f"    ✗ dm_sequence failed: {dm_result.get('error')}")
        return {'dm_sequence': dm_result, 'dm_quality_review': None}

    print(f"    ✓ dm_sequence generated")

    # Quality review COMMENTED OUT - causing false negatives
    # # Run quality review
    # print(f"  - Running quality review...")
    # review_input = {
    #     'linkedin_profile_details_data': profile_data,
    #     'last_30_days_posts_transformed': posts_data,
    #     'perplexity_research': json.dumps(perplexity_data),
    #     'lead_profile': lead_profile_content,
    #     'pain_gain_operational': pain_gain_content,
    #     'dm_sequence': json.dumps(dm_result.get('data', {}))
    # }
    #
    # _, quality_result = run_analysis('dm_quality_review', review_input, None)
    #
    # if not quality_result.get('success'):
    #     print(f"    ⚠ Quality review failed: {quality_result.get('error')}")
    #     return {'dm_sequence': dm_result, 'dm_quality_review': quality_result}
    #
    # quality_data = quality_result.get('data', {})
    # score = quality_data.get('overall_quality_score', 0)
    # recommendation = quality_data.get('approval_recommendation', 'REJECT')
    #
    # print(f"    Quality Score: {score}/10 - {recommendation}")

    return {'dm_sequence': dm_result, 'dm_quality_review': None}


def main():
    parser = argparse.ArgumentParser(description='Lead Research & Personalization Engine')
    parser.add_argument('linkedin_url', help='LinkedIn profile URL')
    parser.add_argument('--post-to-slack', action='store_true',
                        help='Post lead review card to Slack for approval')
    parser.add_argument('--slack-channel', help='Slack channel (overrides env var)')

    args = parser.parse_args()
    linkedin_url = args.linkedin_url

    print("=" * 80)
    print("LEAD RESEARCH & PERSONALIZATION ENGINE")
    print("=" * 80)
    print(f"\nLinkedIn URL: {linkedin_url}\n")

    ensure_tmp_dir()

    # =========================================================================
    # STEP 1: Scrape LinkedIn Profile
    # =========================================================================
    print("[1/5] Scraping LinkedIn profile...")
    linkedin_result = run_tool('scrape_linkedin.py', [linkedin_url])

    if not linkedin_result.get('success'):
        print(f"✗ LinkedIn scraping failed: {linkedin_result.get('error')}")
        sys.exit(1)

    profile_data = linkedin_result['linkedin_profile_details_data']
    posts_data = linkedin_result.get('last_30_days_posts_transformed', '')

    print(f"✓ Profile scraped: {profile_data.get('full_name', 'Unknown')}")
    print(f"  Company: {profile_data.get('company', 'Unknown')}")
    print(f"  Role: {profile_data.get('experiences', [{}])[0].get('title', 'Unknown')}")

    # =========================================================================
    # STEP 2: Research Company & Person (Perplexity)
    # =========================================================================
    print("\n[2/5] Researching company and person (Perplexity)...")

    company = profile_data.get('company', '')
    domain = profile_data.get('company_website', '')
    person = profile_data.get('full_name', '')
    role = profile_data.get('experiences', [{}])[0].get('title', '')

    # Try Perplexity research with retry
    perplexity_result = run_tool('research_with_perplexity.py', [
        '--company', company,
        '--domain', domain,
        '--person', person,
        '--role', role
    ])

    perplexity_failed = False
    if not perplexity_result.get('success'):
        print(f"⚠ Perplexity research failed: {perplexity_result.get('error')}")
        print("  Retrying once...")

        # Retry once
        import time
        time.sleep(2)
        perplexity_result = run_tool('research_with_perplexity.py', [
            '--company', company,
            '--domain', domain,
            '--person', person,
            '--role', role
        ])

        if not perplexity_result.get('success'):
            print(f"✗ Perplexity research failed again: {perplexity_result.get('error')}")
            print("  ⚠ WARNING: Proceeding with LIMITED DATA - DMs may be generic!")
            print("  ⚠ RECOMMENDATION: Manual review required for this lead")
            perplexity_data = {}
            perplexity_failed = True
        else:
            perplexity_data = perplexity_result.get('data', {})
            print(f"✓ Research completed on retry")
            print(f"  Growth signals: {len(perplexity_data.get('growth_signals', []))}")
            print(f"  Employee reviews: {len(perplexity_data.get('employee_review_quotes', []))}")
    else:
        perplexity_data = perplexity_result.get('data', {})
        print(f"✓ Research completed")
        print(f"  Growth signals: {len(perplexity_data.get('growth_signals', []))}")
        print(f"  Employee reviews: {len(perplexity_data.get('employee_review_quotes', []))}")

    # =========================================================================
    # STEP 3: Run AI Analyses (2 parallel + 1 sequential)
    # =========================================================================
    print("\n[3/5] Running AI analyses (2 parallel + 1 sequential)...")

    # Prepare input data for analyses
    analysis_input = {
        'linkedin_profile_details_data': profile_data,
        'last_30_days_posts_transformed': posts_data,
        'perplexity_research': json.dumps(perplexity_data)
    }

    # Define analyses to run in two phases
    # Phase 1: Run lead_profile and pain_gain_operational in parallel (they only need profile + perplexity data)
    # Phase 2: Run dm_sequence sequentially (needs phase 1 results)
    # REMOVED: similarities (not used in DMs), pain_gain_automation (broken/narrow), connection_request (use HeyReach template instead)

    phase1_analyses = [
        ('lead_profile', None),
        ('pain_gain_operational', None)
    ]

    # Run phase 1 analyses in parallel
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_analysis, analysis_type, analysis_input, model): analysis_type
            for analysis_type, model in phase1_analyses
        }

        for future in concurrent.futures.as_completed(futures):
            analysis_type, result = future.result()

            if result.get('success'):
                results[analysis_type] = result
                print(f"  ✓ {analysis_type} completed")
            else:
                print(f"  ✗ {analysis_type} failed: {result.get('error')}")
                results[analysis_type] = result

    # Update analysis input with phase 1 results for dm_sequence
    if results.get('lead_profile', {}).get('success'):
        lead_profile_content = json.dumps(results['lead_profile'].get('data', {}))
        analysis_input['lead_profile'] = lead_profile_content

    if results.get('pain_gain_operational', {}).get('success'):
        pain_gain_content = json.dumps(results['pain_gain_operational'].get('data', {}))
        analysis_input['pain_gain_operational'] = pain_gain_content

    # =========================================================================
    # STEP 3.5: Run DM Sequence (Quality Loop Disabled)
    # =========================================================================
    print("\n[3.5/5] Running DM sequence...")

    dm_results = run_dm_sequence_with_quality_loop(
        analysis_input=analysis_input,
        profile_data=profile_data,
        posts_data=posts_data,
        perplexity_data=perplexity_data,
        lead_profile_content=lead_profile_content if results.get('lead_profile', {}).get('success') else '{}',
        pain_gain_content=pain_gain_content if results.get('pain_gain_operational', {}).get('success') else '{}',
        max_retries=2
    )

    # Store results
    results['dm_sequence'] = dm_results.get('dm_sequence')
    results['dm_quality_review'] = dm_results.get('dm_quality_review')  # Will be None

    # Quality review output COMMENTED OUT (reviewer disabled)
    # # Print final status
    # if results['dm_quality_review'] and results['dm_quality_review'].get('success'):
    #     review_data = results['dm_quality_review'].get('data', {})
    #     score = review_data.get('overall_quality_score', 0)
    #     recommendation = review_data.get('approval_recommendation', 'UNKNOWN')
    #     print(f"\n  Final Quality: {score}/10 - {recommendation}")
    #
    #     if recommendation != 'APPROVE' or score < 8.5:
    #         print(f"  ⚠ Remaining issues:")
    #         for issue in review_data.get('suggested_improvements', [])[:3]:
    #             print(f"    - {issue}")

    # =========================================================================
    # STEP 4: Generate Human Review Report
    # =========================================================================
    print("\n[4/5] Generating human review report...")

    # Build quality flags
    quality_flags = []
    if perplexity_failed:
        quality_flags.append("⚠️ PERPLEXITY_FAILED - Limited company data")
    # Quality review flags COMMENTED OUT (reviewer disabled)
    # if not results.get('dm_quality_review', {}).get('success'):
    #     quality_flags.append("⚠️ QUALITY_REVIEW_FAILED")
    # if results.get('dm_quality_review', {}).get('success'):
    #     score = results['dm_quality_review'].get('data', {}).get('overall_quality_score', 0)
    #     if score < 7:
    #         quality_flags.append(f"⚠️ LOW_QUALITY_SCORE ({score}/10)")

    # Prepare consolidated data
    consolidated_data = {
        'linkedin_url': linkedin_url,
        'profile_data': profile_data,
        'perplexity_data': perplexity_data,
        'quality_flags': quality_flags,
        'requires_manual_review': len(quality_flags) > 0,
        **results  # All analysis results
    }

    # Save consolidated data
    results_file = save_temp_json(consolidated_data, f'results_{linkedin_url.split("/")[-2]}.json')

    # Generate HTML review report
    review_result = run_tool('generate_review_report.py', [
        '--data', results_file
    ])

    review_report_path = ''
    if review_result.get('success'):
        review_report_path = review_result.get('report_path', '')
        print(f"✓ Review report generated")
        print(f"  📄 {review_report_path}")

        # Add review report path to consolidated data
        consolidated_data['review_report_path'] = review_report_path

        # Re-save consolidated data with report path
        results_file = save_temp_json(consolidated_data, f'results_{linkedin_url.split("/")[-2]}.json')
    else:
        print(f"⚠ Review report generation failed: {review_result.get('error')}")

    # =========================================================================
    # STEP 5: Upload to Google Sheets
    # =========================================================================
    print("\n[5/6] Uploading to Google Sheets...")

    # Upload to Google Sheets
    sheets_result = run_tool('update_google_sheet.py', [
        '--linkedin-url', linkedin_url,
        '--data', results_file
    ])

    if sheets_result.get('success'):
        print(f"✓ Sheet {sheets_result.get('action', 'updated')} successfully")
        if sheets_result.get('row'):
            print(f"  Row: {sheets_result.get('row')}")
        if quality_flags:
            print(f"  ⚠ Quality flags: {', '.join(quality_flags)}")
            print(f"  ⚠ REQUIRES MANUAL REVIEW before sending to HeyReach")
        if review_report_path:
            print(f"  📄 Review report: {review_report_path}")
    else:
        print(f"⚠ Google Sheets update failed: {sheets_result.get('error')}")

    # =========================================================================
    # AIRTABLE DISABLED (keeping code for reference)
    # =========================================================================
    # # Upload to Airtable
    # airtable_result = run_tool('airtable_client.py', [
    #     '--action', 'update-lead',
    #     '--linkedin-url', linkedin_url,
    #     '--data', results_file
    # ])

    # =========================================================================
    # STEP 6: Post to Slack (Optional)
    # =========================================================================
    if args.post_to_slack:
        print("\n[6/6] Posting to Slack for review...")

        slack_args = ['--data', results_file]
        if args.slack_channel:
            slack_args.extend(['--channel', args.slack_channel])

        slack_result = run_tool('post_lead_review_to_slack.py', slack_args)

        if slack_result.get('success'):
            print(f"✓ Posted to Slack (channel: {slack_result.get('channel', 'lead-review')})")
            print(f"  Thread: {slack_result.get('thread_ts')}")
            print(f"  Message: {slack_result.get('ts')}")
            print(f"  👉 Review in Slack and click Approve/Reject")
        else:
            print(f"⚠ Slack posting failed: {slack_result.get('error')}")
    else:
        print("\n[6/6] Slack posting skipped (use --post-to-slack to enable)")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("RESEARCH COMPLETE")
    print("=" * 80)
    print(f"\nFull results saved to: {results_file}")

    if review_report_path:
        print(f"\n📄 HUMAN REVIEW REPORT:")
        print(f"   {review_report_path}")
        print(f"   Open this file in your browser to review DMs before sending to HeyReach")

    if quality_flags:
        print(f"\n⚠️  QUALITY REVIEW REQUIRED:")
        for flag in quality_flags:
            print(f"   {flag}")
        print(f"\n   Review the HTML report above before approving for HeyReach")

    # Show key outputs
    print("\n" + "-" * 80)
    print("PERSONALIZED CONNECTION REQUEST:")
    print("-" * 80)
    if results.get('connection_request', {}).get('success'):
        conn_req = results['connection_request'].get('data', {}).get('connection_request', '')
        print(conn_req)
    else:
        print("(Failed to generate)")

    print("\n" + "-" * 80)
    print("LINKEDIN DM SEQUENCE:")
    print("-" * 80)
    if results.get('dm_sequence', {}).get('success'):
        dm_data = results['dm_sequence'].get('data', {})
        print(f"\nDM 1 ({dm_data.get('dm1', {}).get('character_count', 0)} chars):")
        print(dm_data.get('dm1', {}).get('message', ''))
        print(f"\nDM 2 ({dm_data.get('dm2', {}).get('character_count', 0)} chars):")
        print(dm_data.get('dm2', {}).get('message', ''))
        print(f"\nDM 3 ({dm_data.get('dm3', {}).get('character_count', 0)} chars):")
        print(dm_data.get('dm3', {}).get('message', ''))
    else:
        print("(Failed to generate)")

    print("\n" + "=" * 80)
    print("Done!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
