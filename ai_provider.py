"""
Multi-AI Provider Abstraction Layer

Supports OpenAI, Google Gemini, and Anthropic Claude.
Provider is auto-detected from the model name, or falls back to AI_PROVIDER env var.
"""

import os
import logging
from typing import Optional, Any, Protocol
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class CompletionResult:
    """Unified result from any AI provider."""
    text: str
    citations: list = field(default_factory=list)
    raw_response: Any = None


class AIProvider(Protocol):
    """Protocol defining what any AI provider must support."""

    async def complete(
        self,
        prompt: str,
        model: str,
        system_instruction: str = "",
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> CompletionResult:
        """Standard text/JSON completion."""
        ...

    async def web_search(
        self,
        query: str,
        model: str,
    ) -> CompletionResult:
        """Web-grounded search. Returns text + citations."""
        ...


def detect_provider_from_model(model_name: str) -> Optional[str]:
    """Auto-detect provider name from model name prefix."""
    model_lower = model_name.lower().strip()
    if model_lower.startswith("claude"):
        return "anthropic"
    elif model_lower.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    elif model_lower.startswith("gemini"):
        return "google"
    return None


def create_ai_provider(provider_name: str = None, model: str = None) -> AIProvider:
    """
    Factory that creates the appropriate AI provider.

    If `model` is provided, the provider is auto-detected from the model name.
    Otherwise falls back to `provider_name`, then AI_PROVIDER env var.
    """
    load_dotenv(override=True)
    if model:
        detected = detect_provider_from_model(model)
        if detected:
            provider_name = detected
            logger.info(f"Auto-detected provider '{provider_name}' from model '{model}'")
    provider_name = provider_name or os.getenv("AI_PROVIDER", "openai")
    provider_name = provider_name.lower().strip()

    if provider_name == "openai":
        from providers.openai_provider import OpenAIProvider
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        # 確保 API key 只包含 ASCII 字元
        api_key = api_key.encode('ascii', errors='ignore').decode('ascii')
        return OpenAIProvider(api_key=api_key)

    elif provider_name in ("google", "gemini"):
        from providers.gemini_provider import GeminiProvider
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY environment variable is not set.")
        return GeminiProvider(api_key=api_key)

    elif provider_name in ("anthropic", "claude"):
        from providers.anthropic_provider import AnthropicProvider
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        return AnthropicProvider(api_key=api_key)

    else:
        raise ValueError(
            f"Unknown AI provider: '{provider_name}'. "
            f"Supported providers: openai, google, anthropic"
        )
