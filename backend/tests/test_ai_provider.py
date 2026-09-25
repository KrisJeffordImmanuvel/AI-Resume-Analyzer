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

    exc = errors.ClientError(
        400, {"error": {"code": 400, "message": "API key not valid.", "status": "INVALID_ARGUMENT"}}
    )
    with pytest.raises(AIError) as err:
        provider_with(FakeModels(error=exc)).generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert str(err.value) == "gemini-test: 400 INVALID_ARGUMENT: API key not valid."


def test_sdk_does_not_retry_on_its_own():
    # Retries are ours, so they can share one time limit.
    assert GeminiProvider("k", "gemini-test", timeout_seconds=5).http_options.retry_options.attempts == 1


def test_semantic_matching_is_off_unless_enabled(monkeypatch):
    monkeypatch.delenv("SEMANTIC_MATCHING", raising=False)
    assert get_settings().semantic_matching is False
    monkeypatch.setenv("SEMANTIC_MATCHING", "true")
    assert get_settings().semantic_matching is True


class FakeClock:
    """Simulated time: sleeping and slow calls advance it instantly."""

    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class ScriptedModels:
    """generate_content fails or succeeds per model name.

    An outcome can be a list (one entry per attempt, the last one repeats). Each call
    takes `call_seconds` of simulated time.
    """

    def __init__(self, outcomes, clock=None, call_seconds=1.0):
        self.outcomes, self.calls, self.timeouts = outcomes, [], []
        self.clock, self.call_seconds = clock, call_seconds

    def generate_content(self, **kwargs):
        model = kwargs["model"]
        self.calls.append(model)
        self.timeouts.append(kwargs["config"].http_options.timeout / 1000)
        if self.clock:
            if self.call_seconds > self.timeouts[-1]:  # like the SDK: give up at the timeout
                import httpx

                self.clock.now += self.timeouts[-1]
                raise httpx.ReadTimeout("timed out")
            self.clock.now += self.call_seconds
        outcome = self.outcomes[model]
        if isinstance(outcome, list):
            outcome = outcome[min(self.calls.count(model), len(outcome)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def api_error(code, status, message):
    from google.genai import errors

    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"code": code, "message": message, "status": status}})


def two_model_provider(outcomes, timeout_seconds=90, call_seconds=1.0):
    provider = GeminiProvider("k", ["main-model", "backup-model"], timeout_seconds=timeout_seconds)
    clock = FakeClock()
    provider.clock, provider.sleep = clock, clock.sleep
    models = ScriptedModels(outcomes, clock, call_seconds)
    provider._client = type("C", (), {"models": models})()
    return provider, models


def test_overloaded_main_model_falls_back_to_backup():
    ok = FakeResponse(text='{"skills": [], "experience": [], "education": []}')
    provider, models = two_model_provider(
        {"main-model": api_error(503, "UNAVAILABLE", "high demand"), "backup-model": ok}
    )
    provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model"] * 3 + ["backup-model"]  # 3 tries each
    assert provider.model == "backup-model"  # labels show the model that answered


def test_permanent_error_does_not_try_backup():
    provider, models = two_model_provider(
        {
            "main-model": api_error(400, "INVALID_ARGUMENT", "API key not valid."),
            "backup-model": FakeResponse(text="{}"),
        }
    )
    with pytest.raises(AIError, match="API key not valid"):
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model"]


def test_all_models_overloaded_reports_each():
    provider, _ = two_model_provider(
        {
            "main-model": api_error(503, "UNAVAILABLE", "high demand"),
            "backup-model": api_error(429, "RESOURCE_EXHAUSTED", "quota"),
        }
    )
    with pytest.raises(AIError) as err:
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert "main-model: 503" in str(err.value) and "backup-model: 429" in str(err.value)


OK = FakeResponse(text='{"skills": [], "experience": [], "education": []}')


def test_temporary_error_is_retried_after_a_short_wait():
    provider, models = two_model_provider(
        {"main-model": [api_error(503, "UNAVAILABLE", "busy")] * 2 + [OK], "backup-model": OK}
    )
    provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model"] * 3
    assert provider.sleep.__self__.sleeps == [2.0, 4.0]


def test_whole_call_stays_within_the_time_limit():
    # Every attempt is slow and overloaded: without a shared limit this would be
    # 2 models x 3 attempts x 40 s. With the limit it stops at 90 s.
    busy = api_error(503, "UNAVAILABLE", "busy")
    provider, models = two_model_provider({"main-model": busy, "backup-model": busy}, call_seconds=40)
    with pytest.raises(AIError) as err:
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert "main-model: 503" in str(err.value) and "no answer within 90 seconds" in str(err.value)
    clock = provider.sleep.__self__
    assert clock.now <= 90
    # Each attempt may only use the time that is left.
    assert all(t <= 90 for t in models.timeouts) and models.timeouts[0] == 90
    assert models.timeouts == sorted(models.timeouts, reverse=True)


def test_an_attempt_that_times_out_stops_with_a_clear_message():
    import httpx

    provider, models = two_model_provider({"main-model": httpx.ReadTimeout("timed out"), "backup-model": OK})
    with pytest.raises(AIError, match="main-model: no answer within 90 seconds"):
        provider.generate_json(system="s", prompt="p", schema=AIResumeProfile)
    assert models.calls == ["main-model"]


def test_fallback_models_come_from_settings(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("GEMINI_MODEL", "main-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", " backup-a , main-model,backup-b ")
    assert make_provider(get_settings()).models == ["main-model", "backup-a", "backup-b"]


def test_ai_time_limit_default_and_bounds(monkeypatch):
    monkeypatch.delenv("AI_TIMEOUT_SECONDS", raising=False)
    assert get_settings().ai_timeout_seconds == 90
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "1000")
    assert get_settings().ai_timeout_seconds == 240  # always ends before the page gives up
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "1")
    assert get_settings().ai_timeout_seconds == 10
