"""
llm/factory.py
--------------
Factory function that builds the correct LLMClient based on the
LLM_PROVIDER setting, hiding provider-specific wiring from app.py.

To add a new provider later (e.g. Anthropic-native SDK instead of an
OpenAI-compatible endpoint):
    1. Implement a new class satisfying llm.base.LLMClient.
    2. Add an `elif provider == "your_provider":` branch below.
No other file needs to change.
"""

from __future__ import annotations

from config import Settings
from llm.base import LLMClient, LLMClientError
from llm.openai_client import OpenAICompatibleClient

_SUPPORTED_PROVIDERS = ("openai", "groq", "openrouter")


def build_llm_client(settings: Settings) -> LLMClient:
    """Instantiates the LLMClient configured by `settings.llm_provider`."""
    provider = settings.llm_provider

    if provider == "openai":
        return OpenAICompatibleClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            provider_name="OpenAI",
            timeout_seconds=settings.request_timeout_seconds,
        )

    if provider == "groq":
        return OpenAICompatibleClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url=settings.groq_base_url,
            provider_name="Groq",
            timeout_seconds=settings.request_timeout_seconds,
        )

    if provider == "openrouter":
        return OpenAICompatibleClient(
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            provider_name="OpenRouter",
            timeout_seconds=settings.request_timeout_seconds,
        )

    raise LLMClientError(
        f"Unsupported LLM_PROVIDER '{provider}'. "
        f"Supported values are: {', '.join(_SUPPORTED_PROVIDERS)}."
    )
