"""
Employee: OpenAI Analysis Engine
Purpose: Run AI analyses using OpenAI API with different prompts and models

Usage:
    python scripts/analyze_with_openai.py --type lead_profile --input data.json
    python scripts/analyze_with_openai.py --type similarities --input data.json --model gpt-4
    python scripts/analyze_with_openai.py --type connection_request --input data.json

Dependencies:
    - requests
    - python-dotenv

Environment Variables:
    - OPENAI_API_KEY

Supported Analysis Types (uses prompts/lead_research/ templates):
    - lead_profile: Generate person/company profile, interests, unique facts
    - similarities: Find similarities between lead and the company founder
    - pain_gain_operational: Analyze operational gaps (3 Engines framework)
    - pain_gain_automation: Identify automation opportunities
    - connection_request: Generate LinkedIn connection request
    - dm_sequence: Generate 3-message LinkedIn DM sequence

Output:
    JSON object containing the analysis results
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv()

# Model mapping - using actual OpenAI API model names (Dec 2025)
MODELS = {
    "gpt-4": "gpt-4o",
    "gpt-4.1": "gpt-4o",
    "gpt-5": "gpt-5.1",  # GPT-5.1 (previous latest)
    "gpt-5.1": "gpt-5.1",  # GPT-5.1
    "gpt-5.2": "gpt-5.2",  # GPT-5.2 Thinking (latest - Dec 11, 2025)
    "gpt-5.2-pro": "gpt-5.2-pro",  # GPT-5.2 Pro (maximum accuracy)
    "o4-mini": "o1-mini"
}

# Prompt templates directory (lead research prompts)
# Path: scripts/ -> .. -> skill root -> assets/prompts/
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'prompts')


def load_prompt(analysis_type):
    """Load prompt template for analysis type"""
    prompt_file = os.path.join(PROMPTS_DIR, f"{analysis_type}.txt")

    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, 'r') as f:
        return f.read()


def render_prompt(template, data):
    """
    Render prompt template with data
    Replaces placeholders like {{key.subkey}} with values from data dict
    """
    import re

    def replace_match(match):
        path = match.group(1).strip()
        keys = path.split('.')

        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, '')
            else:
                return ''

        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    # Replace {{path.to.value}} with actual values
    rendered = re.sub(r'\{\{(.+?)\}\}', replace_match, template)
    return rendered


def analyze_with_openai(analysis_type, input_data, model=None, additional_context=None):
    """
    Run OpenAI analysis

    Args:
        analysis_type (str): Type of analysis to run
        input_data (dict): Input data for the analysis
        model (str): OpenAI model to use (optional, defaults based on analysis type)
        additional_context (str): Optional additional context to append to prompt (e.g., quality feedback)

    Returns:
        dict: Analysis results
    """
    api_key = os.getenv('OPENAI_API_KEY')
    helicone_key = os.getenv('HELICONE_API_KEY')

    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in .env")

    # Load prompt template
    try:
        prompt_template = load_prompt(analysis_type)
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e)
        }

    # Render prompt with input data
    try:
        prompt = render_prompt(prompt_template, input_data)

        # Append additional context if provided (e.g., quality feedback for retries)
        if additional_context:
            prompt += f"\n\n---\n\n# FEEDBACK FROM PREVIOUS ATTEMPT\n\n{additional_context}\n\nPlease revise your output based on the feedback above while maintaining all other constraints."
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to render prompt: {str(e)}"
        }

    # Determine model
    if not model:
        # Default models for each analysis type (using GPT-5.2 - latest)
        defaults = {
            "lead_profile": "gpt-5.2",  # GPT-5.2 Thinking
            "similarities": "gpt-5.2",  # GPT-5.2 Thinking
            "pain_gain_operational": "gpt-5.2",  # GPT-5.2 Thinking
            "pain_gain_automation": "gpt-5.2",  # GPT-5.2 Thinking
            "connection_request": "gpt-5.2",  # GPT-5.2 Thinking
            "dm_sequence": "gpt-5.2",  # GPT-5.2 Thinking (best for structured work)
            "dm_quality_review": "gpt-5.2"  # GPT-5.2 Thinking
        }
        model = defaults.get(analysis_type, "gpt-4")

    # Map to actual OpenAI model name
    model_name = MODELS.get(model, model)

    # API endpoint - route through Helicone for observability
    if helicone_key:
        url = "https://oai.helicone.ai/v1/chat/completions"
    else:
        url = "https://api.openai.com/v1/chat/completions"

    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Add Helicone auth if available
    if helicone_key:
        headers["Helicone-Auth"] = f"Bearer {helicone_key}"

    # Payload
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }

    # Make request with retry
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            data = response.json()

            # Extract content
            content = data['choices'][0]['message']['content']

            # Try to parse as JSON
            try:
                # Remove markdown code fences if present
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                    content = content.strip()

                analysis_result = json.loads(content)

                return {
                    "success": True,
                    "analysis_type": analysis_type,
                    "model": model_name,
                    "data": analysis_result,
                    "raw_content": content,
                    "raw_response": data
                }
            except json.JSONDecodeError:
                # If not JSON, return raw content
                return {
                    "success": True,
                    "analysis_type": analysis_type,
                    "model": model_name,
                    "data": {"raw": content},
                    "raw_content": content,
                    "warning": "Response was not valid JSON"
                }

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"  Timeout on attempt {attempt + 1}, retrying in 5 seconds...")
                import time
                time.sleep(5)
                continue
            return {
                "success": False,
                "error": "Request timeout after retries"
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"  Rate limit on attempt {attempt + 1}, retrying in 10 seconds...")
                    import time
                    time.sleep(10)
                    continue
                return {
                    "success": False,
                    "error": "Rate limit exceeded after retries",
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

    return {
        "success": False,
        "error": "Max retries exceeded"
    }


def main():
    parser = argparse.ArgumentParser(description='Run OpenAI analysis')
    parser.add_argument('--type', required=True,
                        choices=['lead_profile', 'similarities', 'pain_gain_operational',
                                'pain_gain_automation', 'connection_request', 'dm_sequence',
                                'dm_quality_review'],
                        help='Type of analysis to run')
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--model', help='OpenAI model to use (optional)')
    parser.add_argument('--additional-context', help='Path to JSON file with additional context (optional)')

    args = parser.parse_args()

    # Load input data
    try:
        with open(args.input, 'r') as f:
            input_data = json.load(f)
    except Exception as e:
        print(f"✗ Failed to load input file: {e}")
        sys.exit(1)

    # Load additional context if provided
    additional_context = None
    if args.additional_context:
        try:
            with open(args.additional_context, 'r') as f:
                context_data = json.load(f)
                additional_context = context_data.get('context', '')
        except Exception as e:
            print(f"⚠ Failed to load additional context: {e}")

    print(f"Running {args.type} analysis...")
    if args.model:
        print(f"  Using model: {args.model}")
    if additional_context:
        print(f"  With quality feedback from previous attempt")

    result = analyze_with_openai(args.type, input_data, args.model, additional_context)

    if result['success']:
        print(f"✓ Analysis completed successfully")
        if 'warning' in result:
            print(f"  ⚠ {result['warning']}")
    else:
        print(f"✗ Analysis failed: {result['error']}")
        sys.exit(1)

    # Output JSON to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
