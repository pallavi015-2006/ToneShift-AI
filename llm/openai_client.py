"""
llm/openai_client.py
---------------------
Concrete LLMClient implementation for any OpenAI-compatible Chat
Completions API. This single class serves OpenAI, Groq, and OpenRouter,
because all three implement the same `/chat/completions` schema — only
the base_url, api_key, and model name change.

Retries are handled with `tenacity` for transient network/rate-limit
errors, using exponential backoff, so a single flaky request doesn't
surface as a hard failure to the end user.
"""

from __future__ import annotations

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from llm.base import (
    AuthenticationError,
    InvalidRequestError,
    LLMClient,
    LLMClientError,
    LLMResponse,
    NetworkError,
    RateLimitError,
)


class OpenAICompatibleClient(LLMClient):
    """Chat-completion client for OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        provider_name: str,
        timeout_seconds: int = 30,
    ) -> None:
        if not api_key:
            raise AuthenticationError(
                f"No API key configured for provider '{provider_name}'. "
                f"Set the corresponding *_API_KEY value in your .env file."
            )
        self._model = model
        self._provider_name = provider_name
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((NetworkError, RateLimitError)),
    )
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> LLMResponse:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except openai.AuthenticationError as exc:
            raise AuthenticationError(
                f"Authentication failed for provider '{self._provider_name}'.\n\n"
                f"Actual API Error:\n{exc}"
    ) from exc
        except openai.RateLimitError as exc:
            raise RateLimitError(
                f"Rate limit reached for provider '{self._provider_name}'. "
                f"Please wait a moment and try again."
            ) from exc
        except openai.APITimeoutError as exc:
            raise NetworkError(
                f"Request to '{self._provider_name}' timed out. "
                f"Check your internet connection and try again."
            ) from exc
        except openai.APIConnectionError as exc:
            raise NetworkError(
                f"Could not reach '{self._provider_name}'. "
                f"Check your internet connection and try again."
            ) from exc
        except openai.BadRequestError as exc:
            raise InvalidRequestError(
                f"The request was rejected by '{self._provider_name}': {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMClientError(
                f"Provider '{self._provider_name}' returned an unexpected error: {exc}"
            ) from exc

        choice = completion.choices[0] if completion.choices else None
        if choice is None or not choice.message or not choice.message.content:
            raise LLMClientError(
                f"Provider '{self._provider_name}' returned an empty response."
            )

        usage = completion.usage
        return LLMResponse(
            text=choice.message.content.strip(),
            model=self._model,
            provider=self._provider_name,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
