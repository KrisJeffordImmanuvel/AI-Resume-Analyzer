"""One password for the whole app (APP_PASSWORD), used when it is published as a website."""

import pytest

import auth
from config import get_settings

PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(auth, "limiter", auth.LoginLimiter())


def test_without_password_everything_works_as_before(make_client):
    with make_client() as client:
        assert client.get("/api/auth/status").json() == {"required": False, "signed_in": True}
        assert client.get("/api/analyses").status_code == 200
        assert client.get("/docs").status_code == 200


def test_with_password_data_needs_sign_in(make_client):
    with make_client(password=PASSWORD) as client:
        assert client.get("/api/auth/status").json() == {"required": True, "signed_in": False}
        for path in ("/api/analyses", "/api/jobs", "/api/samples", "/docs", "/redoc", "/openapi.json"):
            r = client.get(path)
            assert r.status_code == 401, path
            assert r.json()["detail"] == "Please sign in first."
        assert client.post("/api/data/delete-all", json={"confirm": "DELETE"}).status_code == 401
        # The health check stays public (Render uses it to see the app is up).
        assert client.get("/health").status_code == 200


def test_sign_in_then_out(make_client):
    with make_client(password=PASSWORD) as client:
        r = client.post("/api/auth/login", json={"password": PASSWORD})
        assert r.status_code == 200
        assert r.json() == {"required": True, "signed_in": True}
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=" in cookie
        assert client.get("/api/analyses").status_code == 200
        assert client.get("/api/auth/status").json()["signed_in"] is True

        assert client.post("/api/auth/logout").json() == {"required": True, "signed_in": False}
        assert client.get("/api/analyses").status_code == 401


def test_wrong_password_is_refused(make_client):
    with make_client(password=PASSWORD) as client:
        r = client.post("/api/auth/login", json={"password": "guess"})
        assert r.status_code == 401
        assert r.json()["detail"] == "That password is not right."
        assert "set-cookie" not in r.headers
        assert client.get("/api/analyses").status_code == 401


def test_forged_or_expired_cookies_are_refused(make_client):
    with make_client(password=PASSWORD) as client:
        settings = get_settings()
        expired = auth.make_token(settings, now=0)
        good = auth.make_token(settings)
        for value in ("", "abc", "9999999999.deadbeef", expired, good[:-1] + ("0" if good[-1] != "0" else "1")):
            client.cookies.set(auth.COOKIE_NAME, value)
            assert client.get("/api/analyses").status_code == 401, value
        client.cookies.set(auth.COOKIE_NAME, good)
        assert client.get("/api/analyses").status_code == 200


def test_changing_the_password_signs_everyone_out(make_client, monkeypatch):
    with make_client(password=PASSWORD) as client:
        client.post("/api/auth/login", json={"password": PASSWORD})
        monkeypatch.setenv("APP_PASSWORD", "a different long password")
        assert client.get("/api/analyses").status_code == 401


def test_too_many_wrong_passwords_are_slowed_down(make_client):
    with make_client(password=PASSWORD) as client:
        for _ in range(5):
            assert client.post("/api/auth/login", json={"password": "nope"}).status_code == 401
        r = client.post("/api/auth/login", json={"password": PASSWORD})
        assert r.status_code == 429
        assert int(r.headers["retry-after"]) > 0
        assert "Too many wrong passwords" in r.json()["detail"]


def test_limiter_forgets_old_tries_and_caps_everyone():
    now = [1000.0]
    limiter = auth.LoginLimiter(per_client=2, overall=3, window=60, clock=lambda: now[0])
    limiter.failed("a")
    limiter.failed("a")
    assert limiter.retry_after("a") > 0
    assert limiter.retry_after("b") == 0
    limiter.failed("b")
    assert limiter.retry_after("c") > 0  # three wrong tries in total: everyone waits
    now[0] += 61
    assert limiter.retry_after("a") == 0
    limiter.failed("a")
    limiter.succeeded("a")
    assert limiter.retry_after("a") == 0


def test_require_password_refuses_to_start_without_a_strong_one(make_client, monkeypatch):
    for weak in ("", "short"):
        with pytest.raises(RuntimeError, match="APP_PASSWORD"):
            client = make_client(password=weak)
            monkeypatch.setenv("REQUIRE_PASSWORD", "true")
            with client:
                pass
    client = make_client(password=PASSWORD)
    monkeypatch.setenv("REQUIRE_PASSWORD", "true")
    with client:
        assert client.get("/health").status_code == 200


def test_require_password_refuses_to_start_without_a_database(make_client, monkeypatch):
    client = make_client(password=PASSWORD)
    monkeypatch.setenv("REQUIRE_PASSWORD", "true")
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with client:
            pass


def test_security_headers(make_client):
    with make_client() as client:
        r = client.get("/health")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "same-origin"
        assert "strict-transport-security" not in r.headers  # only over https
    with make_client() as client:
        https = client.get("https://testserver/health")
        assert https.headers["strict-transport-security"].startswith("max-age=")


def test_cookie_is_secure_over_https(make_client):
    with make_client(password=PASSWORD) as client:
        r = client.post("https://testserver/api/auth/login", json={"password": PASSWORD})
        assert "secure" in r.headers["set-cookie"].lower()


def test_dev_server_can_send_the_cookie(make_client):
    with make_client(password=PASSWORD) as client:
        r = client.options(
            "/api/analyses",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-credentials"] == "true"
