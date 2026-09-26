import pytest

from tests.conftest import TEST_DATABASE_URL


def test_health_without_api_key_uses_fallback(make_client):
    with make_client(api_key="") as client:
        body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["ai_configured"] is False
    assert body["demo_mode"] is False
    assert body["ai_mode"] == "fallback"
    assert body["fallback_reason"] == "no_api_key"
    assert body["database"] == "ok"


def test_health_with_api_key_is_live(make_client):
    with make_client(api_key="placeholder-test-key") as client:
        body = client.get("/health").json()

    assert body["ai_configured"] is True
    assert body["ai_mode"] == "live"
    assert body["fallback_reason"] is None


def test_demo_mode_forces_fallback_even_with_key(make_client):
    with make_client(api_key="placeholder-test-key", demo_mode="true") as client:
        body = client.get("/health").json()

    assert body["ai_configured"] is True
    assert body["demo_mode"] is True
    assert body["ai_mode"] == "fallback"
    assert body["fallback_reason"] == "demo_mode"


@pytest.mark.skipif(bool(TEST_DATABASE_URL), reason="checks the SQLite file")
def test_database_file_is_created_on_startup(make_client, tmp_path):
    with make_client() as client:
        client.get("/health")

    assert (tmp_path / "test.db").exists()


def test_cors_allows_vite_dev_server(make_client):
    with make_client() as client:
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_openapi_documents_health_fields(make_client):
    with make_client() as client:
        schema = client.get("/openapi.json").json()

    ref = schema["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    fields = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]
    assert set(fields) == {
        "status",
        "version",
        "ai_configured",
        "demo_mode",
        "ai_mode",
        "fallback_reason",
        "database",
        "ai_model",
        "semantic_matching",
        "ai_timeout_seconds",
    }
