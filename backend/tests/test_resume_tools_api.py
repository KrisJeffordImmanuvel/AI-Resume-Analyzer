from pathlib import Path

from tests.conftest import FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FILES = {
    "resume": ("r.txt", (SAMPLES / "sample_resume.txt").read_bytes()),
    "jd_file": ("jd.txt", (SAMPLES / "sample_job_description.txt").read_bytes()),
}


def new_analysis(client) -> int:
    return client.post("/api/analyses", files=FILES).json()["id"]


def test_quality_and_ats_endpoints(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        quality = client.get(f"/api/analyses/{aid}/quality")
        ats = client.get(f"/api/analyses/{aid}/ats")
    assert quality.status_code == 200 and ats.status_code == 200
    assert quality.json()["summary"]["bullets"] == 7
    assert ats.json()["parse"]["headings"] == ["Summary", "Experience", "Skills", "Education"]


def test_rewrite_workspace_saves_history(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        first = client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "- Responsible for building dashboards"})
        second = client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "- Helped the team ship releases"})
        history = client.get(f"/api/analyses/{aid}/rewrites").json()
    assert first.status_code == 201
    assert first.json()["source"] == "fallback"
    assert first.json()["variants"][0]["text"].startswith("Built dashboards")
    assert [h["id"] for h in history] == [second.json()["id"], first.json()["id"]]


def test_ai_rewrite_through_api(make_client):
    provider = FakeProvider({"variants": [{"text": "Built dashboards for [N teams].", "note": "n"}]})
    with make_client(api_key="placeholder", provider=provider) as client:
        aid = new_analysis(client)
        body = client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "- Built dashboards"}).json()
    assert body["source"] == "ai"
    assert body["variants"][0]["placeholders"] == ["[N teams]"]


def test_validation_and_not_found(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        blank = client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "   "})
        too_long = client.post(f"/api/analyses/{aid}/rewrites", json={"bullet": "x" * 601})
        missing = [
            client.get("/api/analyses/999/quality"),
            client.get("/api/analyses/999/ats"),
            client.post("/api/analyses/999/rewrites", json={"bullet": "x"}),
            client.get("/api/analyses/999/rewrites"),
        ]
    assert blank.status_code == 422 and too_long.status_code == 422
    assert [r.status_code for r in missing] == [404, 404, 404, 404]


def test_career_endpoint(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        resp = client.get(f"/api/analyses/{aid}/career")
        missing = client.get("/api/analyses/999/career")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["roles"]) == 10
    assert body["timeline"]["roles"] == 2
    assert "from" in body["timeline"]["gaps"][0] if body["timeline"]["gaps"] else True
    assert missing.status_code == 404
