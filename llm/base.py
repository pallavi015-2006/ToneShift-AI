"""
llm/base.py
-----------
Defines the abstract contract every LLM provider client must implement.

This is the key architectural seam that lets ToneShift swap between
OpenAI, Groq, and OpenRouter (or any future provider) without touching
app.py or prompts/templates.py. All three providers listed above expose
OpenAI-compatible Chat Completions APIs, so in practice a single
concrete implementation (OpenAICompatibleClient) satisfies this
interface for all of them — only the base_url/api_key/model differ.

Any future provider with a genuinely different API surface (e.g. a
provider that isn't OpenAI-compatible) can implement this same
LLMClient interface without changing calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response returned by any LLM client implementation."""

    text: str
    model: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMClientError(Exception):
    """Base exception for all LLM client failures.

    app.py catches this (and its subclasses) to render clean,
    user-facing error messages instead of raw stack traces.
    """


class AuthenticationError(LLMClientError):
    """Raised when the API key is missing, malformed, or rejected."""


class RateLimitError(LLMClientError):
    """Raised when the provider throttles the request."""


class NetworkError(LLMClientError):
    """Raised for connectivity/timeout failures reaching the provider."""


class InvalidRequestError(LLMClientError):
    """Raised when the provider rejects the request payload itself."""


class LLMClient(ABC):
    """Abstract base class for a chat-completion LLM provider client."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> LLMResponse:
        """Sends a chat completion request and returns a normalized response.

        Args:
            system_prompt: Instructions establishing the assistant's role
                and constraints (tone rules, output format rules).
            user_prompt: The concrete task, including the original text.
            temperature: Sampling temperature in [0.0, 1.0], controls
                creativity/randomness of the rewrite.

        Raises:
            AuthenticationError: invalid/missing API key.
            RateLimitError: provider-side throttling.
            NetworkError: timeout or connection failure.
            InvalidRequestError: malformed request / bad model name / etc.
            LLMClientError: any other provider failure.
        """
        raise NotImplementedError
