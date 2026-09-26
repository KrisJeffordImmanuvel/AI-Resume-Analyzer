"""The backend serves the built frontend, so the whole app runs at one address."""

import pytest


@pytest.fixture
def dist(tmp_path, monkeypatch):
    folder = tmp_path / "dist"
    (folder / "assets").mkdir(parents=True)
    (folder / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (folder / "assets" / "index-abc123.js").write_text("console.log('app')", encoding="utf-8")
    (folder / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("do not serve", encoding="utf-8")
    monkeypatch.setenv("FRONTEND_DIST", str(folder))
    return folder


def test_root_serves_index(make_client, dist):
    with make_client() as client:
        r = client.get("/")
    assert r.status_code == 200
    assert "id=root" in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_unknown_page_path_falls_back_to_index(make_client, dist):
    with make_client() as client:
        r = client.get("/some/page")
    assert r.status_code == 200
    assert "id=root" in r.text


def test_built_assets_are_cached_long(make_client, dist):
    with make_client() as client:
        r = client.get("/assets/index-abc123.js")
        icon = client.get("/favicon.svg")
    assert r.status_code == 200
    assert "console.log" in r.text
    assert "immutable" in r.headers["cache-control"]
    assert icon.status_code == 200
    assert icon.headers["cache-control"] == "no-cache"


def test_api_routes_still_work(make_client, dist):
    with make_client() as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/docs").status_code == 200
        assert client.get("/api/analyses").status_code == 200


def test_unknown_api_path_is_json_404_not_the_page(make_client, dist):
    with make_client() as client:
        r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


def test_files_outside_build_folder_are_not_served(make_client, dist):
    with make_client() as client:
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt"):
            r = client.get(path)
            assert "do not serve" not in r.text


def test_missing_build_shows_friendly_page(make_client, tmp_path, monkeypatch):
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path / "nowhere"))
    with make_client() as client:
        r = client.get("/")
        assert client.get("/health").status_code == 200
    assert r.status_code == 503
    assert "has not been built yet" in r.text
    assert "start.ps1" in r.text


def test_every_app_page_address_serves_the_app(make_client, dist):
    # The pages (React Router) live in the browser; the server answers each address with the app.
    with make_client() as client:
        for path in ["/seeker", "/seeker/analysis/12/roadmap", "/provider/new", "/provider/jobs/3/report/7/career"]:
            r = client.get(path)
            assert r.status_code == 200, path
            assert "id=root" in r.text, path
