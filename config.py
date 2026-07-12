"""
config.py
---------
Centralized, fail-fast configuration loader for ToneShift.

This module is the single source of truth for environment-driven settings.
It reads values from a `.env` file (via python-dotenv) and exposes them as
typed, validated constants so the rest of the application never touches
`os.environ` directly.

Design rationale (for viva/demo):
    - Separation of concerns: no other module parses environment variables.
    - Fail-fast: obviously malformed numeric settings raise immediately at
      import time rather than causing confusing bugs mid-conversion.
    - Provider abstraction: LLM_PROVIDER decides which client the factory
      in llm/factory.py will instantiate, without any other module caring.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from a local .env file if present. Real deployment
# environments (Docker, Streamlit Cloud, etc.) can set env vars directly,
# in which case this is a harmless no-op.
load_dotenv(override=True)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(
            f"Environment variable '{name}' must be a number, got: {raw!r}"
        )


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"Environment variable '{name}' must be an integer, got: {raw!r}"
        )


@dataclass(frozen=True)
class Settings:
    """Immutable application settings resolved once at startup."""

    llm_provider: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    groq_api_key: str
    groq_model: str
    groq_base_url: str
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    request_timeout_seconds: int
    max_input_characters: int
    default_temperature: float


def load_settings() -> Settings:
    """Builds a Settings object from the current environment."""
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip(),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o").strip(),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        request_timeout_seconds=_get_int("REQUEST_TIMEOUT_SECONDS", 30),
        max_input_characters=_get_int("MAX_INPUT_CHARACTERS", 6000),
        default_temperature=_get_float("DEFAULT_TEMPERATURE", 0.7),
    )


# A single shared instance, imported by other modules as:
#   from config import settings
settings = load_settings()

# Human-friendly tone catalogue shown in the UI dropdown.
# Kept here (not hardcoded in app.py) so prompts/templates.py and app.py
# both reference the same canonical list.
SUPPORTED_TONES: list[str] = [
    "Formal",
    "Friendly",
    "Professional",
    "Casual",
    "Academic",
    "Persuasive",
    "Funny",
    "Motivational",
    "Child Friendly",
    "Email",
    "Social Media",
    "Customer Support",
]

# Maps a user-facing length label to an approximate word-count instruction.
RESPONSE_LENGTH_MAP: dict[str, str] = {
    "Short": "Keep the response concise: roughly 40-60% of the original word count.",
    "Medium": "Keep the response close to the original length (roughly the same word count).",
    "Long": "Expand slightly where natural: roughly 130-160% of the original word count.",
}
