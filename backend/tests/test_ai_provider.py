import pytest

from ai_provider import AIError, GeminiProvider, make_provider
from config import get_settings
from profile_extraction import AIResumeProfile


class FakeModels:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class FakeResponse:
    def __init__(self, parsed=None, text=None):
        self.parsed, self.text = parsed, text


def provider_with(models):
    provider = GeminiProvider("secret-key-123", "gemini-test", timeout_seconds=5)
    provider._client = type("C", (), {"models": models})()
    return provider


def test_parsed_response_is_returned_as_dict():
    parsed = AIResumeProfile(skills=[], experience=[], education=[])
    models = FakeModels(FakeResponse(parsed=parsed))
    out = provider_with(models).generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert out == {"skills": [], "experience": [], "education": []}
    config = models.kwargs["config"]
    assert models.kwargs["model"] == "gemini-test"
    assert config.response_mime_type == "application/json"
    assert config.temperature == 0
    assert config.system_instruction == "s"


def test_text_json_is_validated_when_parsed_is_missing():
    models = FakeModels(FakeResponse(text='{"skills": [], "experience": [], "education": []}'))
    out = provider_with(models).generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert out["skills"] == []


def test_invalid_json_raises_ai_error():
    models = FakeModels(FakeResponse(text="not json"))
    with pytest.raises(AIError, match="not valid JSON"):
        provider_with(models).generate_json(system="s", prompt="p", schema=AIResumeProfile)


def test_sdk_errors_become_ai_errors_without_the_key():
    models = FakeModels(error=RuntimeError("bad key secret-key-123 rejected"))
    with pytest.raises(AIError) as err:
        provider_with(models).generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert "secret-key-123" not in str(err.value)
    assert "***" in str(err.value)


def test_make_provider_respects_key_and_demo_mode(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    assert make_provider(get_settings()) is None
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    monkeypatch.setenv("DEMO_MODE", "true")
    assert make_provider(get_settings()) is None
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom")
    provider = make_provider(get_settings())
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-custom"


def test_google_api_errors_are_summarised_in_one_line():
    from google.genai import errors

    exc = errors.ClientError(400, {"error": {"code": 400, "message": "API key not valid.", "status": "INVALID_ARGUMENT"}})
    with pytest.raises(AIError) as err:
        provider_with(FakeModels(error=exc)).generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert str(err.value) == "gemini-test: 400 INVALID_ARGUMENT: API key not valid."


def test_temporary_errors_are_retried_but_permanent_ones_are_not():
    provider = GeminiProvider("k", "gemini-test", timeout_seconds=5)
    retry = provider.http_options.retry_options
    assert retry.attempts == 3
    assert 503 in retry.http_status_codes and 429 in retry.http_status_codes
    assert 400 not in retry.http_status_codes and 404 not in retry.http_status_codes


def test_semantic_matching_is_off_unless_enabled(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MATCHING", raising=False)
    assert get_settings().semantic_matching is False
    monkeypatch.setenv("SEMANTIC_MATCHING", "true")
    assert get_settings().semantic_matching is True


class ScriptedModels:
    """generate_content fails or succeeds per model name."""

    def __init__(self, outcomes):
        self.outcomes, self.calls = outcomes, []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs["model"])
        outcome = self.outcomes[kwargs["model"]]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def api_error(code, status, message):
    from google.genai import errors

    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"code": code, "message": message, "status": status}})


def two_model_provider(outcomes):
    provider = GeminiProvider("k", ["main-model", "backup-model"], timeout_seconds=5)
    models = ScriptedModels(outcomes)
    provider._client = type("C", (), {"models": models})()
    return provider, models


def test_overloaded_main_model_falls_back_to_backup():
    ok = FakeResponse(text='{"skills": [], "experience": [], "education": []}')
    provider, models = two_model_provider({"main-model": api_error(503, "UNAVAILABLE", "high demand"),
                                           "backup-model": ok})
    provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model", "backup-model"]
    assert provider.model == "backup-model"  # labels show the model that answered


def test_permanent_error_does_not_try_backup():
    provider, models = two_model_provider({"main-model": api_error(400, "INVALID_ARGUMENT", "API key not valid."),
                                           "backup-model": FakeResponse(text="{}")})
    with pytest.raises(AIError, match="API key not valid"):
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model"]


def test_all_models_overloaded_reports_each():
    provider, _ = two_model_provider({"main-model": api_error(503, "UNAVAILABLE", "high demand"),
                                      "backup-model": api_error(429, "RESOURCE_EXHAUSTED", "quota")})
    with pytest.raises(AIError) as err:
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert "main-model: 503" in str(err.value) and "backup-model: 429" in str(err.value)


def test_fallback_models_come_from_settings(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("GEMINI_MODEL", "main-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", " backup-a , main-model,backup-b ")
    assert make_provider(get_settings()).models == ["main-model", "backup-a", "backup-b"]
