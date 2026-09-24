from pathlib import Path

from github_check import GitHubError
from tests.conftest import FakeGitHub

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FILES = {
    "resume": ("r.txt", (SAMPLES / "sample_resume.txt").read_bytes()),
    "jd_file": ("jd.txt", (SAMPLES / "sample_job_description.txt").read_bytes()),
}
REPOS = [{"name": "api", "html_url": "https://github.com/example/api", "language": "Python", "fork": False,
          "topics": ["fastapi"], "pushed_at": "2026-01-01T00:00:00Z"}]


def new_analysis(client) -> int:
    return client.post("/api/analyses", files=FILES).json()["id"]


def test_github_uses_resume_link_when_no_username_given_and_is_saved(make_client):
    gh = FakeGitHub(REPOS)
    with make_client(github=gh) as client:
        aid = new_analysis(client)
        before = client.get(f"/api/analyses/{aid}/evidence").json()
        resp = client.post(f"/api/analyses/{aid}/github", json={})
        after = client.get(f"/api/analyses/{aid}/evidence").json()
    assert before == {"detected_github_username": "example", "github": None, "linkedin": None}
    assert resp.status_code == 201, resp.text
    assert gh.calls[0] == ("user", "example")
    assert after["github"]["id"] == resp.json()["id"]
    assert {c["skill"] for c in resp.json()["resume_claims"] if c["status"] == "seen"} == {"Python", "FastAPI"}


def test_github_errors_are_422_with_message(make_client):
    gh = FakeGitHub(error=GitHubError("No public GitHub user with that username."))
    with make_client(github=gh) as client:
        aid = new_analysis(client)
        resp = client.post(f"/api/analyses/{aid}/github", json={"username": "ghost"})
        bad = client.post(f"/api/analyses/{aid}/github", json={"username": "not valid"})
    assert resp.status_code == 422 and "No public GitHub user" in resp.json()["detail"]
    assert bad.status_code == 422


def test_linkedin_and_fairness_endpoints(make_client):
    with make_client() as client:
        aid = new_analysis(client)
        li = client.post(f"/api/analyses/{aid}/linkedin",
                         json={"text": "Experience\nSoftware Engineer\nExample Fintech Pvt Ltd\n2022 - Present"})
        blank = client.post(f"/api/analyses/{aid}/linkedin", json={"text": "   "})
        fair = client.get(f"/api/analyses/{aid}/fairness")
        saved = client.get(f"/api/analyses/{aid}/evidence").json()
    assert li.status_code == 201, li.text
    assert [r["status"] for r in li.json()["roles"]][-1] == "consistent"
    assert blank.status_code == 422 and "LinkedIn text" in blank.json()["detail"]
    assert fair.status_code == 200 and fair.json()["resume"] == []
    assert saved["linkedin"]["id"] == li.json()["id"]


def test_evidence_endpoints_404(make_client):
    with make_client() as client:
        codes = [client.get("/api/analyses/999/evidence").status_code,
                 client.post("/api/analyses/999/github", json={"username": "x"}).status_code,
                 client.post("/api/analyses/999/linkedin", json={"text": "x"}).status_code,
                 client.get("/api/analyses/999/fairness").status_code]
    assert codes == [404, 404, 404, 404]
