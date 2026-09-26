import pytest
from fastapi.testclient import TestClient


class FakeProvider:
    """Stands in for Gemini. Returns a canned response or raises a canned error."""

    name = "fake"
    model = "fake-model"

    def __init__(self, response: dict | None = None, error: Exception | None = None):
        self.response = response or {"skills": [], "experience": [], "education": []}
        self.error = error
        self.calls = []

    def generate_json(self, *, system, prompt, schema):
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self.error:
            raise self.error
        return self.response


class FakeEmbedder:
    """Deterministic stand-in for Sentence Transformers.

    Each text gets the vector of the first keyword it contains; any other text
    gets its own axis, so it is orthogonal (similarity 0) to everything else. Pick vectors to get the
    cosine similarities a test needs, e.g. [1, 0] vs [0.8, 0.6] -> 0.8.
    """

    def __init__(self, keyword_vectors: dict[str, list[float]] | None = None, error: Exception | None = None):
        self.keyword_vectors = keyword_vectors or {}
        self.error = error
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        if self.error:
            raise self.error
        base = 3
        out = []
        for i, text in enumerate(texts):
            vector = [0.0] * (base + len(texts))
            keyword = next((v for k, v in self.keyword_vectors.items() if k in text), None)
            if keyword is None:
                vector[base + i] = 1.0  # unrelated: its own axis, orthogonal to all others
            else:
                vector[: len(keyword)] = keyword
            out.append(vector)
        return out


class FakeGitHub:
    """Stands in for the GitHub API. `repos_data` is a list of repo dicts like GitHub returns."""

    def __init__(self, repos_data=None, error=None, user_data=None):
        self.repos_data = repos_data or []
        self.error = error
        self.user_data = user_data
        self.calls = []

    def user(self, username):
        self.calls.append(("user", username))
        if self.error:
            raise self.error
        return self.user_data or {
            "login": username,
            "html_url": f"https://github.com/{username}",
            "public_repos": len(self.repos_data),
            "followers": 0,
        }

    def repos(self, username):
        self.calls.append(("repos", username))
        return self.repos_data


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Build a TestClient with a throwaway SQLite DB and controlled AI settings.

    Explicitly sets/clears every setting so a developer's real backend\\.env
    never leaks into tests, and replaces the AI provider and embedder so no
    test ever calls Gemini or downloads a model.
    """
    from main import app
    from routers.common import get_ai_provider, get_embedder
    from routers.evidence import get_github_client

    def _make(
        api_key: str = "", demo_mode: str = "false", provider=None, embedder=None, github=None, password: str = ""
    ) -> TestClient:
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
        monkeypatch.setenv("DEMO_MODE", demo_mode)
        monkeypatch.setenv("SEMANTIC_MATCHING", "false")
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
        monkeypatch.delenv("SEMANTIC_THRESHOLD", raising=False)
        monkeypatch.setenv("APP_PASSWORD", password)
        monkeypatch.delenv("SESSION_SECRET", raising=False)
        monkeypatch.delenv("REQUIRE_PASSWORD", raising=False)
        if api_key:
            monkeypatch.setenv("GOOGLE_API_KEY", api_key)
        else:
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        app.dependency_overrides[get_ai_provider] = lambda: provider
        app.dependency_overrides[get_embedder] = lambda: embedder
        app.dependency_overrides[get_github_client] = lambda: github or FakeGitHub()
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()
