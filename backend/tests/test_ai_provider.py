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
    assert str(err.value) == "400 INVALID_ARGUMENT: API key not valid."
