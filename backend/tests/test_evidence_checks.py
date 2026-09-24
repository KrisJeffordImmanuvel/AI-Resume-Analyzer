from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from fairness import fairness_scan
from github_check import GitHubError, detect_username, github_check, language_skill
from linkedin_check import linkedin_check
from parsing import normalize_text
from profile_extraction import extract_profile
from tests.conftest import FakeGitHub, FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
RESUME = normalize_text((SAMPLES / "sample_resume.txt").read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)
TODAY = date(2026, 9, 24)

REPOS = [
    {"name": "api", "html_url": "https://github.com/p/api", "language": "Python", "fork": False,
     "description": "FastAPI + PostgreSQL service", "topics": ["docker", "rest-api"], "pushed_at": "2026-05-01T00:00:00Z"},
    {"name": "infra", "html_url": "https://github.com/p/infra", "language": "HCL", "fork": False,
     "topics": [], "pushed_at": "2023-01-01T00:00:00Z"},
    {"name": "someone-elses", "html_url": "https://github.com/p/fork", "language": "Rust", "fork": True},
    {"name": "old", "html_url": "https://github.com/p/old", "language": "Go", "archived": True},
]


# ---- GitHub ------------------------------------------------------------------------

def test_username_is_detected_from_resume_links_only():
    assert detect_username(RESUME) == "example"
    assert detect_username("see github.com/orgs/acme and github.com/jane-doe") == "jane-doe"
    assert detect_username("no links") is None


@pytest.mark.parametrize("lang, skill", [("Python", "Python"), ("Shell", "Bash"), ("HCL", "Terraform"),
                                         ("Dockerfile", "Docker"), ("Vue", "Vue.js"), ("Makefile", None)])
def test_github_languages_map_to_skills(lang, skill):
    assert language_skill(lang) == skill


def test_github_check_uses_only_public_non_fork_repos_and_marks_evidence_source():
    out = github_check("p", RESUME, FakeGitHub(REPOS), NOW)
    assert out["repos_analyzed"] == 2  # fork and archived repo excluded
    assert out["recently_active_repos"] == 1
    seen = {c["skill"]: c for c in out["resume_claims"] if c["status"] == "seen"}
    assert set(seen) == {"Python", "FastAPI", "PostgreSQL", "Docker", "REST APIs"}
    assert seen["Python"]["examples"][0]["via"] == "main language: Python"
    assert seen["FastAPI"]["examples"][0] == {"name": "api", "url": "https://github.com/p/api",
                                              "pushed_at": "2026-05-01T00:00:00Z", "via": "topics/description"}
    assert {c["skill"] for c in out["resume_claims"] if c["status"] == "not_seen"} >= {"Django", "Redis"}
    assert [l["language"] for l in out["not_on_resume"]] == ["HCL"]
    assert "not mean untrue" in out["label"]


@pytest.mark.parametrize("bad", ["", "-dash", "a" * 40, "name with space", "x/y"])
def test_invalid_usernames_are_rejected_before_any_request(bad):
    client = FakeGitHub()
    with pytest.raises(GitHubError):
        github_check(bad, RESUME, client, NOW)
    assert client.calls == []


def test_github_errors_propagate_as_user_messages():
    with pytest.raises(GitHubError, match="No public GitHub user"):
        github_check("ghost", RESUME, FakeGitHub(error=GitHubError("No public GitHub user with that username.")), NOW)


# ---- LinkedIn ----------------------------------------------------------------------

LINKEDIN = """Priya Raman
Backend Engineer at Example Fintech
Experience
Software Engineer
Example Fintech Pvt Ltd · Full-time
2021 - Present
Junior Developer
Sample Retail Co
2020 - 2022
Skills: Python, Kubernetes, FastAPI"""


def run_linkedin(text=LINKEDIN, provider=None):
    profile = extract_profile(RESUME, None, "no_api_key")
    return linkedin_check(text, RESUME, profile, "fallback", provider, "no_api_key", TODAY)


def test_linkedin_layout_roles_are_matched_and_date_differences_quoted():
    out = run_linkedin()
    rows = {r["status"]: r for r in out["roles"]}
    assert set(rows) == {"date_mismatch", "consistent"}
    mismatch = rows["date_mismatch"]
    assert mismatch["detail"] == "start 2022 - Present vs 2021 - Present"
    assert mismatch["resume"] == "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)"
    assert mismatch["linkedin"] == "Software Engineer\nExample Fintech Pvt Ltd · Full-time\n2021 - Present"
    assert rows["consistent"]["linkedin"] in normalize_text(LINKEDIN)


def test_linkedin_skill_differences():
    skills = run_linkedin()["skills"]
    assert "Python" in skills["both"] and "FastAPI" in skills["both"]
    assert skills["only_linkedin"] == [{"skill": "Kubernetes", "quote": "Skills: Python, Kubernetes, FastAPI"}]
    assert "Redis" in skills["only_resume"]


def test_linkedin_roles_missing_on_either_side():
    text = "Experience\nData Scientist\nOther Corp\n2018 - 2019"
    statuses = sorted(r["status"] for r in run_linkedin(text)["roles"])
    assert statuses == ["only_linkedin", "only_resume", "only_resume"]


def test_linkedin_without_dates_gets_a_notice():
    assert any("No dated roles" in n for n in run_linkedin("Just a headline about me")["notices"])


def test_linkedin_ai_path_uses_verified_extraction():
    provider = FakeProvider({"skills": [], "education": [], "experience": [
        {"title": "Software Engineer", "organization": "Example Fintech Pvt Ltd", "dates": "2021 - Present",
         "quote": "Software Engineer\nExample Fintech Pvt Ltd · Full-time\n2021 - Present"},
        {"title": "CTO", "organization": "Google", "dates": "2015 - 2016", "quote": "CTO at Google 2015"}]})
    out = run_linkedin(provider=provider)
    assert out["source"] == "ai"
    assert all("Google" not in (r["linkedin"] or "") for r in out["roles"])  # invented role discarded
    assert any("different methods" in n for n in out["notices"])  # resume was read without AI


# ---- Fairness ----------------------------------------------------------------------

def test_fairness_flags_jd_wording_with_all_terms_per_line():
    jd = ("We want a rockstar Python ninja to join our young, energetic team.\n"
          "Native English speakers only.\nMust be a citizen.\nCompetitive salary and a great culture.")
    findings = fairness_scan("", jd)["job_description"]
    got = {(f["category"], tuple(f["terms"])) for f in findings}
    assert ("Gender-coded", ("rockstar", "ninja")) in got
    assert ("Age-coded", ("young", "energetic")) in got
    assert ("Exclusionary requirement", ("Native English speakers",)) in got
    assert ("Check if legally required", ("Must be a citizen",)) in got
    assert all(f["quote"] in jd for f in findings)
    assert len(findings) == 4  # "Competitive salary" and "great culture" are fine


def test_fairness_flags_personal_details_in_resume_but_not_ordinary_words():
    resume = ("Jane Doe\nDate of Birth: 01/02/1999\nMarital Status: Single\nMarried\n"
              "Father's Name: X\nReligion: Y\nI married data and design.\nBuilt a singleton cache.")
    findings = fairness_scan(resume, "")["resume"]
    quotes = [f["quote"] for f in findings]
    assert quotes == ["Date of Birth: 01/02/1999", "Marital Status: Single", "Married", "Religion: Y",
                      "Father's Name: X"]
    assert fairness_scan(RESUME, "")["resume"] == []


# ---- Real HTTP client, with canned responses (no network) --------------------------

import httpx  # noqa: E402

from github_check import HttpGitHubClient  # noqa: E402


def client_with(handler, token=""):
    return HttpGitHubClient(token=token, transport=httpx.MockTransport(handler))


def test_http_client_requests_public_endpoints_and_sends_token_only_if_set():
    seen = []

    def handler(request):
        seen.append((request.url.path, dict(request.url.params), request.headers.get("authorization")))
        return httpx.Response(200, json={"login": "p"} if request.url.path == "/users/p" else [])

    client_with(handler).user("p")
    client_with(handler, token="tok").repos("p")
    assert seen[0] == ("/users/p", {}, None)
    assert seen[1][0] == "/users/p/repos" and seen[1][1]["type"] == "owner" and seen[1][2] == "Bearer tok"


@pytest.mark.parametrize("status, headers, message", [
    (404, {}, "No public GitHub user"),
    (403, {"x-ratelimit-remaining": "0"}, "hourly limit"),
    (500, {}, r"GitHub returned an error \(500\)"),
])
def test_http_client_maps_errors_to_friendly_messages(status, headers, message):
    client = client_with(lambda request: httpx.Response(status, headers=headers, json={}))
    with pytest.raises(GitHubError, match=message):
        client.user("p")


def test_http_client_network_failure_is_friendly():
    def handler(request):
        raise httpx.ConnectError("offline")

    with pytest.raises(GitHubError, match="Could not reach GitHub"):
        client_with(handler).user("p")


def test_linkedin_duration_text_does_not_hide_the_role_title():
    text = ("Experience\nSoftware Engineer\nExample Fintech Pvt Ltd · Full-time\n"
            "Jan 2021 - Present · 5 yrs 9 mos")
    rows = run_linkedin(text)["roles"]
    mismatch = next(r for r in rows if r["status"] == "date_mismatch")
    assert mismatch["linkedin"].startswith("Software Engineer\nExample Fintech")


def test_topics_match_case_sensitive_skills_exactly():
    from github_check import _topic_skill

    assert _topic_skill("react") == "React"
    assert _topic_skill("rest-api") == "REST APIs"
    assert _topic_skill("nodejs") == "Node.js"
    assert _topic_skill("awesome-list") is None
