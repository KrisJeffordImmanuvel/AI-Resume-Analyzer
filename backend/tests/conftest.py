import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Build a TestClient with a throwaway SQLite DB and controlled AI settings.

    Explicitly sets/clears every setting so a developer's real backend\\.env
    never leaks into tests.
    """

    def _make(api_key: str = "", demo_mode: str = "false") -> TestClient:
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
        monkeypatch.setenv("DEMO_MODE", demo_mode)
        if api_key:
            monkeypatch.setenv("GOOGLE_API_KEY", api_key)
        else:
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        from main import app

        return TestClient(app)

    return _make
