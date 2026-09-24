"""AI provider layer. The rest of the app talks to AIProvider, never to an SDK.

Tests replace the provider with a fake, so no test ever calls a real AI service.
"""

import json
from typing import Protocol

from pydantic import BaseModel

from config import Settings


class AIError(Exception):
    """The AI call failed. The message is safe to show to the user."""


class AIProvider(Protocol):
    name: str
    model: str

    def generate_json(self, *, system: str, prompt: str, schema: type[BaseModel]) -> dict: ...


def _safe_message(exc: Exception, secret: str) -> str:
    """Short, user-safe description of a provider error, with the API key scrubbed."""
    code, message = getattr(exc, "code", None), getattr(exc, "message", None)
    if code and message:  # google.genai APIError: "400 INVALID_ARGUMENT: API key not valid..."
        text = f"{code} {getattr(exc, 'status', '') or ''}: {message}"
    else:
        text = f"{type(exc).__name__}: {exc}"
    if secret:
        text = text.replace(secret, "***")
    text = " ".join(text.split())
    return text[:300]


# Temporary errors (rate limit, overload) are retried a couple of times before
# giving up and falling back; permanent ones (bad key, unknown model) are not.
RETRY_ATTEMPTS = 3  # including the first request
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float):
        from google import genai
        from google.genai import types

        self._types = types
        self._api_key = api_key
        self.model = model
        self.http_options = types.HttpOptions(
            timeout=int(timeout_seconds * 1000),  # milliseconds
            retry_options=types.HttpRetryOptions(
                attempts=RETRY_ATTEMPTS,
                initial_delay=2.0,
                max_delay=8.0,
                http_status_codes=RETRY_STATUS_CODES,
            ),
        )
        self._client = genai.Client(api_key=api_key, http_options=self.http_options)

    def generate_json(self, *, system: str, prompt: str, schema: type[BaseModel]) -> dict:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0,
                    automatic_function_calling=self._types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        except Exception as exc:  # network, auth, quota, bad model name...
            raise AIError(_safe_message(exc, self._api_key)) from exc

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed.model_dump()
        text = getattr(response, "text", None)
        if not text:
            raise AIError("The AI returned an empty response.")
        try:
            return schema.model_validate(json.loads(text)).model_dump()
        except Exception as exc:
            raise AIError("The AI response was not valid JSON for the expected format.") from exc


def make_provider(settings: Settings) -> AIProvider | None:
    """Return a provider when AI is enabled, else None (callers then use fallbacks)."""
    if not settings.ai_enabled:
        return None
    return GeminiProvider(settings.google_api_key, settings.gemini_model, settings.ai_timeout_seconds)
