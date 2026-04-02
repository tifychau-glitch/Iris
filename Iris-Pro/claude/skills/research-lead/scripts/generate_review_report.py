#!/usr/bin/env python3
"""
Employee: Generate Human Review Report
Purpose: Creates HTML review report for human approval before HeyReach

Usage:
    python scripts/generate_review_report.py --data results.json

Output:
    HTML report in deliverables/review/
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Paths — skill-relative (scripts/ -> skill root -> project root)
SKILL_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = SKILL_ROOT.parent.parent.parent  # research-lead -> skills -> .claude -> project root
REVIEW_DIR = PROJECT_ROOT / 'deliverables' / 'review'


def generate_html_report(data):
    """Generate beautiful HTML review report"""

    # Extract data
    profile = data.get('profile_data', {})
    dm_sequence = data.get('dm_sequence', {}).get('data', {})
    # Handle dm_quality_review = None (when quality reviewer is disabled)
    quality_review_result = data.get('dm_quality_review') or {}
    quality_review = quality_review_result.get('data', {})
    pain_gain = data.get('pain_gain_operational', {}).get('data', {})
    perplexity = data.get('perplexity_data', {})
    quality_flags = data.get('quality_flags', [])

    name = profile.get('full_name', 'Unknown')
    company = profile.get('company', 'Unknown')
    role = profile.get('experiences', [{}])[0].get('title', 'Unknown')
    linkedin_url = data.get('linkedin_url', '#')

    # Handle quality review being disabled (None/empty)
    quality_score = quality_review.get('overall_quality_score', 'N/A') if quality_review else 'N/A (Reviewer Disabled)'
    approval_rec = quality_review.get('approval_recommendation', 'UNKNOWN') if quality_review else 'N/A'

    # Color coding (handle quality_score being string when reviewer disabled)
    if isinstance(quality_score, (int, float)):
        score_color = '#22c55e' if quality_score >= 8 else '#f59e0b' if quality_score >= 6 else '#ef4444'
    else:
        score_color = '#9ca3af'  # Gray when N/A
    approval_badge = {
        'APPROVE': '<span style="background: #22c55e; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">✓ APPROVE</span>',
        'REVISE': '<span style="background: #f59e0b; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">⚠ REVISE</span>',
        'REJECT': '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">✗ REJECT</span>',
        'UNKNOWN': '<span style="background: #6b7280; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">? UNKNOWN</span>'
    }.get(approval_rec, approval_rec)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Review: {name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.9; font-size: 16px; }}
        .section {{ padding: 24px; border-bottom: 1px solid #e5e5e5; }}
        .section:last-child {{ border-bottom: none; }}
        .section h2 {{ font-size: 18px; color: #1f2937; margin-bottom: 16px; font-weight: 600; }}
        .quality-score {{
            background: {score_color};
            color: white;
            display: inline-block;
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 24px;
            font-weight: bold;
            margin-right: 12px;
        }}
        .dm-box {{
            background: #f9fafb;
            border-left: 4px solid #667eea;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 4px;
        }}
        .dm-box .dm-header {{ color: #667eea; font-weight: 600; margin-bottom: 8px; font-size: 14px; }}
        .dm-box .dm-text {{ color: #374151; font-size: 15px; line-height: 1.7; white-space: pre-wrap; }}
        .citation {{
            background: #ecfdf5;
            border-left: 3px solid #10b981;
            padding: 12px;
            margin: 8px 0;
            font-size: 14px;
            border-radius: 4px;
        }}
        .citation strong {{ color: #059669; }}
        .flag {{
            background: #fef3c7;
            border: 1px solid #fbbf24;
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
            color: #92400e;
        }}
        .check {{ color: #10b981; margin-right: 6px; }}
        .cross {{ color: #ef4444; margin-right: 6px; }}
        .info-grid {{ display: grid; grid-template-columns: 120px 1fr; gap: 12px; }}
        .info-grid dt {{ font-weight: 600; color: #6b7280; }}
        .info-grid dd {{ color: #1f2937; }}
        .approval-actions {{
            display: flex;
            gap: 16px;
            padding: 24px;
            background: #f9fafb;
        }}
        .btn {{
            flex: 1;
            padding: 16px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-approve {{ background: #22c55e; color: white; }}
        .btn-approve:hover {{ background: #16a34a; }}
        .btn-reject {{ background: #ef4444; color: white; }}
        .btn-reject:hover {{ background: #dc2626; }}
        .metadata {{ font-size: 12px; color: #9ca3af; padding: 16px; background: #f9fafb; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>{name}</h1>
            <p>{role} @ {company}</p>
            <p style="font-size: 14px; margin-top: 8px; opacity: 0.8;">
                <a href="{linkedin_url}" target="_blank" style="color: white; text-decoration: underline;">View LinkedIn Profile →</a>
            </p>
        </div>
"""

    # Quality Score Section
    html += f"""
        <!-- Quality Score -->
        <div class="section">
            <h2>Quality Assessment</h2>
            <div style="margin-bottom: 16px;">
                <span class="quality-score">{quality_score}/10</span>
                {approval_badge}
            </div>
"""

    if quality_flags:
        html += """<div style="margin-top: 16px;"><strong style="color: #dc2626;">⚠️ Quality Flags:</strong></div>"""
        for flag in quality_flags:
            html += f'<div class="flag">{flag}</div>'
    else:
        html += '<p style="color: #10b981;">✓ No quality issues detected</p>'

    html += """
        </div>
"""

    # DM Sequence Section with Source Citations
    html += """
        <!-- DM Sequence -->
        <div class="section">
            <h2>LinkedIn DM Sequence with Source Citations</h2>
"""

    # Get source data for citations
    linkedin_posts = data.get('last_30_days_posts_transformed', '')
    posts_list = []
    if linkedin_posts:
        # Parse posts if available
        import re
        post_matches = re.findall(r'Post \d+:.*?(?=Post \d+:|$)', linkedin_posts, re.DOTALL)
        posts_list = [p.strip() for p in post_matches[:3]]  # Top 3 posts

    perplexity_growth = perplexity.get('growth_signals', [])
    perplexity_citations = perplexity.get('citations', [])

    for i, dm_key in enumerate(['dm1', 'dm2', 'dm3'], 1):
        dm = dm_sequence.get(dm_key, {})
        message = dm.get('message', 'N/A')
        char_count = dm.get('character_count', 0)
        hook = dm.get('hook_used', dm.get('gap_referenced', ''))

        html += f"""
            <div class="dm-box">
                <div class="dm-header">DM {i} ({char_count} characters)</div>
                <div class="dm-text">{message}</div>
"""
        if hook:
            html += f"""
                <div class="citation">
                    <strong>📌 Angle/Hook Used:</strong> {hook}
                </div>
"""

        # Try to find source attribution from pain_gain data
        hook_source = None
        source_detail = None

        # Check if hook matches Perplexity growth signals
        if perplexity_growth:
            for growth in perplexity_growth:
                if isinstance(growth, dict):
                    signal = growth.get('signal', '')
                    if signal and (signal.lower() in hook.lower() or hook.lower() in signal.lower()):
                        hook_source = "Perplexity Research"
                        source_detail = f"Growth Signal: {signal}"
                        if growth.get('source'):
                            source_detail += f"<br>📎 <a href=\"{growth.get('source')}\" target=\"_blank\" style=\"color: #667eea;\">{growth.get('source')}</a>"
                        break

        # Check if hook relates to LinkedIn posts
        if not hook_source and posts_list:
            for idx, post in enumerate(posts_list, 1):
                # Simple check if any keywords from hook appear in post
                hook_keywords = hook.lower().split()[:3]  # First 3 words
                if any(keyword in post.lower() for keyword in hook_keywords if len(keyword) > 3):
                    hook_source = "LinkedIn Activity"
                    source_detail = f"From recent LinkedIn post:<br><em style=\"font-size: 13px; color: #6b7280;\">{post[:200]}...</em>"
                    break

        # Default source
        if not hook_source:
            hook_source = "LinkedIn Profile Analysis"
            source_detail = f"Derived from profile data: {profile.get('experiences', [{}])[0].get('title', 'Role')} at {profile.get('company', 'Company')}"

        if hook_source:
            html += f"""
                <div class="citation" style="background: #f0f9ff; border-left-color: #0ea5e9;">
                    <strong>📊 Source:</strong> {hook_source}<br>
                    {source_detail}
                </div>
"""
        html += """
            </div>
"""

    html += """
        </div>
"""

    # Research Citations Section
    html += """
        <!-- Research Citations -->
        <div class="section">
            <h2>Research & Citations</h2>
"""

    # Show verified facts from quality review
    verified_facts = quality_review.get('research_accuracy_check', {}).get('verified_facts', [])
    if verified_facts:
        for fact in verified_facts:
            claim = fact.get('claim_in_dm', '')
            source = fact.get('source', '')
            accurate = fact.get('accurate', False)
            icon = '✓' if accurate else '✗'
            color = '#10b981' if accurate else '#ef4444'

            html += f"""
            <div class="citation">
                <span style="color: {color}; font-weight: bold;">{icon}</span>
                <strong>Claim:</strong> "{claim}"<br>
                <strong>Source:</strong> {source}
            </div>
"""

    # Company data with sources
    if perplexity:
        company_profile = perplexity.get('company_profile', {})
        scale_signals = perplexity.get('scale_signals', {})
        growth_signals = perplexity.get('growth_signals', [])
        citations = perplexity.get('citations', [])

        html += """
            <div style="margin-top: 20px;">
                <strong style="color: #667eea;">🔍 Company Intelligence (Perplexity Research):</strong>
"""

        if company_profile:
            html += f"""
                <div class="citation">
                    <strong>Industry:</strong> {company_profile.get('industry', 'N/A')}<br>
                    <strong>Founded:</strong> {company_profile.get('founded', 'N/A')}<br>
                    <strong>Description:</strong> {company_profile.get('description', 'N/A')[:200]}...
                </div>
"""

        if scale_signals:
            html += f"""
                <div class="citation">
                    <strong>Scale:</strong> {scale_signals.get('employee_count', 'Unknown')} employees,
                    {scale_signals.get('office_count', 'Unknown')} offices
                </div>
"""

        if growth_signals:
            html += '<div class="citation"><strong>Growth Signals Used in DMs:</strong><ul style="margin: 8px 0; padding-left: 20px;">'
            for signal in growth_signals[:5]:  # Top 5
                if isinstance(signal, dict):
                    signal_text = signal.get('signal', str(signal))
                    source_url = signal.get('source', '')
                    if source_url:
                        html += f'<li>{signal_text}<br>📎 <a href="{source_url}" target="_blank" style="color: #667eea; font-size: 12px;">{source_url[:60]}...</a></li>'
                    else:
                        html += f"<li>{signal_text}</li>"
                else:
                    html += f"<li>{signal}</li>"
            html += '</ul></div>'

        # Show Perplexity citations/sources
        if citations:
            html += '<div class="citation" style="background: #fef3c7; border-left-color: #f59e0b;"><strong>📚 Perplexity Source Links:</strong><ul style="margin: 8px 0; padding-left: 20px;">'
            for idx, citation in enumerate(citations[:5], 1):
                if isinstance(citation, dict):
                    url = citation.get('url', citation.get('source', ''))
                    title = citation.get('title', f'Source {idx}')
                elif isinstance(citation, str):
                    url = citation
                    title = f'Source {idx}'
                else:
                    continue

                if url:
                    html += f'<li><a href="{url}" target="_blank" style="color: #d97706;">{title}</a><br><span style="font-size: 11px; color: #78716c;">{url[:80]}...</span></li>'
            html += '</ul></div>'

    # Show LinkedIn Posts Used
    if posts_list:
        html += """
            <div style="margin-top: 20px;">
                <strong style="color: #0a66c2;">💼 LinkedIn Recent Activity:</strong>
"""
        for idx, post in enumerate(posts_list[:3], 1):
            html += f"""
                <div class="citation" style="background: #eff6ff; border-left-color: #0a66c2;">
                    <strong>Recent Post {idx}:</strong><br>
                    <em style="font-size: 13px; color: #374151;">{post[:300]}{'...' if len(post) > 300 else ''}</em>
                </div>
"""
        html += """
            </div>
"""

    html += """
            </div>
        </div>
"""

    # Quality Review Details
    personalization = quality_review.get('personalization_check', {})
    best_practices = quality_review.get('best_practices_check', {})
    flow_check = quality_review.get('flow_check', {})

    html += """
        <!-- Quality Review Details -->
        <div class="section">
            <h2>Quality Review Details</h2>
            <dl class="info-grid">
"""

    checks = [
        ('Actual Name Used', personalization.get('uses_actual_name')),
        ('Actual Company', personalization.get('uses_actual_company')),
        ('Specific (Not Generic)', personalization.get('specific_not_generic')),
        ('DM1 No Pitch', best_practices.get('dm1_no_pitch')),
        ('DM2 Adds Value', best_practices.get('dm2_adds_value')),
        ('DM3 Clear Ask', best_practices.get('dm3_clear_ask')),
        ('Character Limits OK', best_practices.get('character_limits')),
        ('Logical Flow', flow_check.get('logical_bridges')),
    ]

    for label, status in checks:
        icon = '<span class="check">✓</span>' if status else '<span class="cross">✗</span>'
        html += f"""
                <dt>{label}</dt>
                <dd>{icon} {'Pass' if status else 'Fail'}</dd>
"""

    html += """
            </dl>
        </div>
"""

    # Reasoning
    reasoning = quality_review.get('reasoning', 'No reasoning provided')
    html += f"""
        <!-- AI Recommendation Reasoning -->
        <div class="section">
            <h2>AI Recommendation Reasoning</h2>
            <p style="color: #374151; line-height: 1.8;">{reasoning}</p>
        </div>
"""

    # Footer metadata
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html += f"""
        <div class="metadata">
            Generated: {timestamp} | Lead Research System v1.0
        </div>
    </div>
</body>
</html>
"""

    return html


def main():
    parser = argparse.ArgumentParser(description='Generate human review report')
    parser.add_argument('--data', required=True, help='Path to research results JSON')

    args = parser.parse_args()

    # Load data
    try:
        with open(args.data, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        sys.exit(1)

    # Generate report
    html = generate_html_report(data)

    # Create filename
    profile = data.get('profile_data', {})
    name = profile.get('full_name', 'unknown').lower().replace(' ', '_')
    filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    # Save report
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REVIEW_DIR / filename

    with open(report_path, 'w') as f:
        f.write(html)

    print(f"✓ Review report generated: {report_path}")

    # Output JSON
    result = {
        "success": True,
        "report_path": str(report_path),
        "filename": filename
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
