"""
Employee: Perplexity Company & Person Researcher
Purpose: Deep research on company and person using Perplexity AI

Usage:
    python scripts/research_with_perplexity.py --company "Company Name" --domain "company.com" --person "Full Name" --role "Job Title"

Dependencies:
    - requests
    - python-dotenv

Environment Variables:
    - PERPLEXITY_API_KEY

Output:
    JSON object containing:
    - company_domain_verified
    - company_profile
    - scale_signals
    - growth_signals
    - org_structure_signals
    - hiring_patterns
    - tech_stack_evidence
    - employee_review_quotes
    - leader_facts
"""

import os
import sys
import json
import re
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

# JSON schema for response_format — forces Perplexity to return structured output
RESEARCH_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "schema": {
            "type": "object",
            "properties": {
                "company_domain_verified": {"type": "string"},
                "company_profile": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "industry": {"type": "string"},
                        "founded": {"type": "string"},
                        "headquarters": {"type": "string"},
                        "source_url": {"type": "string"}
                    }
                },
                "scale_signals": {
                    "type": "object",
                    "properties": {
                        "employee_count": {"type": "string"},
                        "office_count": {"type": "string"},
                        "office_locations": {"type": "array", "items": {"type": "string"}},
                        "countries_operating": {"type": "array", "items": {"type": "string"}},
                        "source_urls": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "growth_signals": {"type": "array", "items": {"type": "object"}},
                "org_structure_signals": {"type": "array", "items": {"type": "object"}},
                "hiring_patterns": {"type": "array", "items": {"type": "object"}},
                "tech_stack_evidence": {"type": "array", "items": {"type": "object"}},
                "ai_transformation_signals": {"type": "array", "items": {"type": "object"}},
                "employee_review_quotes": {"type": "array", "items": {"type": "object"}},
                "leader_facts": {"type": "array", "items": {"type": "object"}}
            },
            "required": [
                "company_domain_verified", "company_profile", "scale_signals",
                "growth_signals", "org_structure_signals", "hiring_patterns",
                "tech_stack_evidence", "ai_transformation_signals",
                "employee_review_quotes", "leader_facts"
            ]
        }
    }
}


def extract_json(content):
    """Extract JSON from response, handling markdown fences and extra text."""
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fenced = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', content, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Find first { ... } block
    brace_match = re.search(r'\{.*\}', content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def load_perplexity_prompt():
    """Load Perplexity research prompt from prompts directory"""
    # Path: scripts/ -> .. -> skill root -> assets/prompts/
    prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'prompts')
    prompt_file = os.path.join(prompt_dir, 'perplexity_research.txt')

    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, 'r') as f:
        content = f.read()

    # Split into system and user sections
    parts = content.split('---')

    if len(parts) < 2:
        raise ValueError("Prompt file must contain system and user sections separated by '---'")

    system_section = parts[0].strip()
    user_section = parts[1].strip()

    # Extract system prompt (everything after "# System Prompt")
    system_prompt = system_section.replace('# System Prompt', '').strip()

    # Extract user prompt template (everything after "# User Prompt Template")
    user_prompt_template = user_section.replace('# User Prompt Template', '').strip()

    return system_prompt, user_prompt_template


def research_with_perplexity(company_name, company_domain, person_name, person_role):
    """
    Research company and person using Perplexity AI

    Args:
        company_name (str): Name of the company
        company_domain (str): Company website domain
        person_name (str): Full name of the person
        person_role (str): Person's job title

    Returns:
        dict: Research results
    """
    api_key = os.getenv('PERPLEXITY_API_KEY')
    helicone_key = os.getenv('HELICONE_API_KEY')

    if not api_key:
        raise ValueError("Missing PERPLEXITY_API_KEY in .env")

    # Load prompts from file
    try:
        system_prompt, user_prompt_template = load_perplexity_prompt()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Perplexity prompt file missing: {e}")

    # Fill in user prompt template with actual values
    user_prompt = user_prompt_template.replace('{{company_name}}', company_name)
    user_prompt = user_prompt.replace('{{company_domain}}', company_domain)
    user_prompt = user_prompt.replace('{{person_name}}', person_name)
    user_prompt = user_prompt.replace('{{person_role}}', person_role)

    # API endpoint - route through Helicone for observability
    if helicone_key:
        url = "https://perplexity.helicone.ai/chat/completions"
    else:
        url = "https://api.perplexity.ai/chat/completions"

    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Add Helicone auth if available
    if helicone_key:
        headers["Helicone-Auth"] = f"Bearer {helicone_key}"

    # Payload — response_format forces structured JSON output
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "response_format": RESEARCH_JSON_SCHEMA
    }

    # Make request
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()

        # Extract content from response
        content = data['choices'][0]['message']['content']

        # Parse JSON — response_format should guarantee valid JSON,
        # but extract_json handles edge cases (markdown fences, extra text)
        research_data = extract_json(content)
        if research_data:
            return {
                "success": True,
                "data": research_data,
                "citations": data.get("citations", []),
                "raw_response": data
            }
        else:
            return {
                "success": False,
                "error": "Perplexity returned unparseable content",
                "raw_content": content,
                "raw_response": data
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout - Perplexity research took too long"
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            return {
                "success": False,
                "error": "Rate limit exceeded - wait 60 seconds and retry",
                "status_code": 429
            }
        else:
            return {
                "success": False,
                "error": f"HTTP error: {e.response.status_code} - {e.response.text}",
                "status_code": e.response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Research company and person using Perplexity AI')
    parser.add_argument('--company', required=True, help='Company name')
    parser.add_argument('--domain', required=True, help='Company website domain')
    parser.add_argument('--person', required=True, help='Person full name')
    parser.add_argument('--role', required=True, help='Person job title')

    args = parser.parse_args()

    print(f"Researching {args.company} and {args.person}...")

    result = research_with_perplexity(
        args.company,
        args.domain,
        args.person,
        args.role
    )

    if result['success']:
        print(f"\n✓ Research completed successfully")
        data = result['data']
        print(f"  Company verified: {data.get('company_domain_verified', 'Unknown')}")
        print(f"  Scale signals: {len(data.get('scale_signals', {}))} found")
        print(f"  Growth signals: {len(data.get('growth_signals', []))} found")
        print(f"  Employee reviews: {len(data.get('employee_review_quotes', []))} quotes")
    else:
        print(f"\n✗ Research failed: {result['error']}")
        sys.exit(1)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
