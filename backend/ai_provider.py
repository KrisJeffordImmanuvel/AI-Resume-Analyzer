"""AI provider layer. The rest of the app talks to AIProvider, never to an SDK.

Tests replace the provider with a fake, so no test ever calls a real AI service.
"""

import json
import time
from typing import Protocol

import httpx
from pydantic import BaseModel

from config import Settings


class AIError(Exception):
    """The AI call failed. The message is safe to show to the user."""


class AIProvider(Protocol):
    name: str
    model: str

    def generate_json(self, *, system: str, prompt: str, schema: type[BaseModel]) -> dict: ...


def safe_message(exc: Exception, secret: str) -> str:
    """Short, user-safe description of a provider error, with the API key scrubbed."""
    code, message = getattr(exc, "code", None), getattr(exc, "message", None)
    if code and message:  # google.genai APIError: "400 INVALID_ARGUMENT: API key not valid..."
        text = f"{code} {getattr(exc, 'status', '') or ''}: {message}"
    else:
        text = f"{type(exc).__name__}: {exc}"
    if len(secret) >= 8:  # real keys are long; a tiny value would mangle ordinary words
        text = text.replace(secret, "***")
    text = " ".join(text.split())
    return text[:300]


# Temporary errors (rate limit, overload) are retried a couple of times before
# giving up and falling back; permanent ones (bad key, unknown model) are not.
RETRY_ATTEMPTS = 3  # per model, including the first request
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
RETRY_DELAYS = [2.0, 4.0]  # seconds before the 2nd and 3rd attempt
MIN_ATTEMPT_SECONDS = 5.0  # don't start an attempt with less time than this left


class GeminiProvider:
    """Gemini via the Google Gen AI SDK.

    `models` is tried in order: if a model is still overloaded or rate-limited
    after its retries, the next one is used. Permanent errors (bad key, unknown
    model) stop immediately. After a call, `model` names the model that answered.

    `timeout_seconds` limits the whole call, including every retry and backup
    model, so a request never waits longer than that for AI.
    """

    name = "gemini"
    # Replaceable in tests.
    clock = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)

    def __init__(self, api_key: str, models: list[str] | str, timeout_seconds: float):
        from google import genai
        from google.genai import types

        self._types = types
        self._api_key = api_key
        self.models = [models] if isinstance(models, str) else list(models)
        self.model = self.models[0]
        self.timeout_seconds = timeout_seconds
        # Retries happen in _request (not inside the SDK) so they share one time limit.
        self.http_options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
        self._client = genai.Client(api_key=api_key, http_options=self.http_options)

    def _call(self, model: str, system: str, prompt: str, schema: type[BaseModel], timeout: float):
        return self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0,
                automatic_function_calling=self._types.AutomaticFunctionCallingConfig(disable=True),
                http_options=self._types.HttpOptions(timeout=int(timeout * 1000)),  # milliseconds
            ),
        )

    def _request(self, system: str, prompt: str, schema: type[BaseModel]):
        deadline = self.clock() + self.timeout_seconds
        errors = []
        for model in self.models:
            last_error = None
            for attempt in range(RETRY_ATTEMPTS):
                if attempt:
                    wait = RETRY_DELAYS[attempt - 1]
                    if deadline - self.clock() - wait < MIN_ATTEMPT_SECONDS:
                        break  # not enough time left for another attempt
                    self.sleep(wait)
                remaining = deadline - self.clock()
                if errors or attempt or model != self.models[0]:
                    if remaining < MIN_ATTEMPT_SECONDS:
                        break  # the first attempt always runs; later ones need time left
                try:
                    response = self._call(model, system, prompt, schema, timeout=remaining)
                    self.model = model
                    return response
                except httpx.TimeoutException as exc:
                    # This attempt used up the remaining time.
                    errors.append(f"{model}: no answer within {self.timeout_seconds:g} seconds")
                    raise AIError("; ".join(errors)[:600]) from exc
                except Exception as exc:  # network, auth, quota, bad model name...
                    last_error = f"{model}: {safe_message(exc, self._api_key)}"
                    if getattr(exc, "code", None) not in RETRY_STATUS_CODES:
                        # Permanent problem: retrying or another model will not help.
                        raise AIError("; ".join([*errors, last_error])[:600]) from exc
            if last_error:
                errors.append(last_error)
            if model != self.models[-1] and deadline - self.clock() < MIN_ATTEMPT_SECONDS:
                errors.append(f"stopped after {self.timeout_seconds:g} seconds (AI_TIMEOUT_SECONDS)")
                break
        raise AIError("; ".join(errors)[:600])

    def generate_json(self, *, system: str, prompt: str, schema: type[BaseModel]) -> dict:
        response = self._request(system, prompt, schema)

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
    models = [settings.gemini_model] + [m for m in settings.gemini_fallback_models if m != settings.gemini_model]
    return GeminiProvider(settings.google_api_key, models, settings.ai_timeout_seconds)
