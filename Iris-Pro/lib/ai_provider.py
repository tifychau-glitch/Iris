"""
AI Provider Abstraction — All reasoning routes through this.

Supports multiple backends. Switch providers by setting AI_PROVIDER in .env
or ai_provider in args/preferences.yaml.

Providers:
    claude-cli   — Claude Code CLI (subscription-based, no API key needed). Default.
    anthropic    — Direct Anthropic API (needs ANTHROPIC_API_KEY)
    openai       — OpenAI API (needs OPENAI_API_KEY)
    google       — Google Gemini API (needs GEMINI_API_KEY)

Usage:
    from lib.ai_provider import ai

    response = ai.reason("System prompt", "User message")
    response = ai.reason(system, msg, tier="fast")
    response = ai.reason(system, msg, tier="powerful", timeout=180)

Tiers:
    default   — Everyday work (sonnet-class)
    fast      — Low latency (sonnet/flash-class)
    cheap     — High volume (haiku/mini-class)
    powerful  — Complex reasoning (opus/o3-class)
"""

import json
import os
import subprocess
from pathlib import Path

# Legacy model names → abstract tiers
_LEGACY_TO_TIER = {
    "opus": "powerful",
    "sonnet": "default",
    "haiku": "cheap",
}


def _load_preferences() -> dict:
    """Load args/preferences.yaml once at import time."""
    prefs_path = Path(__file__).parent.parent / "args" / "preferences.yaml"
    if not prefs_path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        # Fallback: basic YAML parsing for simple key: value lines
        result = {}
        for line in prefs_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip().strip('"').strip("'")
        return result
    with open(prefs_path) as f:
        return yaml.safe_load(f) or {}


_PREFS = _load_preferences()


class AIProvider:
    """Thin abstraction over AI backends."""

    def __init__(self, provider: str = None):
        self.provider = (
            provider
            or os.getenv("AI_PROVIDER")
            or _PREFS.get("ai_provider")
            or "claude-cli"
        )
        self._tiers = _PREFS.get("model_tiers", {})

    def resolve_model(self, tier: str = None, model: str = None) -> str:
        """Resolve a tier or legacy name to a LiteLLM model string.

        Priority: explicit model kwarg > tier > "default"
        """
        if model:
            # Already a full LiteLLM string (e.g. "openai/gpt-4o")
            if "/" in model:
                return model
            # Legacy name (e.g. "sonnet" → tier "default")
            tier = _LEGACY_TO_TIER.get(model, tier or "default")

        tier = tier or "default"
        provider_key = self.provider if self.provider != "claude-cli" else "anthropic"
        provider_tiers = self._tiers.get(provider_key, {})
        return provider_tiers.get(tier, provider_tiers.get("default", f"{provider_key}/unknown"))

    def reason(
        self,
        system_prompt: str,
        user_message: str = "",
        timeout: int = 120,
        tier: str = None,
        **kwargs,
    ) -> str:
        """Send a reasoning request to the configured AI backend.

        Args:
            system_prompt: System-level instructions.
            user_message: The user's message (appended after system prompt).
            timeout: Max seconds to wait.
            tier: Model tier — "default", "fast", "cheap", "powerful".

        Returns:
            The AI's response text.
        """
        if self.provider == "claude-cli":
            return self._claude_cli(system_prompt, user_message, timeout)
        return self._llm_api(system_prompt, user_message, timeout, tier, **kwargs)

    def _claude_cli(self, system: str, message: str, timeout: int) -> str:
        """Route through Claude Code CLI (subscription-based)."""
        prompt = system
        if message:
            prompt += f"\n\nUser: {message}"

        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                return f"[AI error] CLI exit {result.returncode}: {result.stderr[:200]}"

            data = json.loads(result.stdout)
            return data.get("result", "").strip()

        except subprocess.TimeoutExpired:
            return "[AI error] Request timed out."
        except (json.JSONDecodeError, KeyError):
            return result.stdout.strip() if result.stdout else "[AI error] Parse failure."

    def _llm_api(self, system: str, message: str, timeout: int, tier: str = None, **kwargs) -> str:
        """Route through LiteLLM (handles Anthropic, OpenAI, Google, and 100+ others)."""
        try:
            import litellm
        except ImportError:
            return (
                "[AI error] litellm not installed. "
                "Run: pip install litellm\n"
                "Or switch to claude-cli (no extra deps): AI_PROVIDER=claude-cli"
            )

        model = self.resolve_model(tier=tier, model=kwargs.pop("model", None))
        max_tokens = kwargs.pop("max_tokens", 4096)

        try:
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[AI error] {e}"


# Singleton — import and use directly
ai = AIProvider()
