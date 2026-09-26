from urllib.parse import parse_qs, urlparse

from ai_provider import AIError
from roadmap import build_roadmap, youtube_search_url
from tests.conftest import FakeProvider

EV = {"quote": "q", "term": None, "term_offset": None, "similarity": None}


def result():
    return {
        "matched": [
            {
                "skill": "Python",
                "category": "Programming Languages",
                "priority": "required",
                "credit": 1.0,
                "match_type": "exact",
                "resume_evidence": [EV],
                "jd_evidence": [EV],
            },
            {
                "skill": "CI/CD",
                "category": "DevOps & Infrastructure",
                "priority": "required",
                "credit": 0.5,
                "match_type": "ai_inferred",
                "resume_evidence": [{**EV, "quote": "used GitHub Actions"}],
                "jd_evidence": [EV],
            },
        ],
        "missing": [
            {"skill": "Terraform", "category": "DevOps & Infrastructure", "priority": "preferred", "jd_evidence": [EV]},
            {"skill": "Kubernetes", "category": "DevOps & Infrastructure", "priority": "required", "jd_evidence": [EV]},
        ],
    }


def test_youtube_link_is_a_real_search_url():
    url = youtube_search_url("C++ & CI/CD")
    parsed = urlparse(url)
    assert (parsed.scheme, parsed.netloc, parsed.path) == ("https", "www.youtube.com", "/results")
    assert parse_qs(parsed.query)["search_query"] == ["C++ & CI/CD tutorial"]


def test_fallback_roadmap_orders_gaps_and_uses_templates():
    roadmap = build_roadmap(result(), None, "no_api_key")
    assert roadmap["source"] == "fallback"
    assert roadmap["fallback_reason"] == "no_api_key"
    assert [(i["skill"], i["kind"]) for i in roadmap["items"]] == [
        ("Kubernetes", "learn"),
        ("CI/CD", "strengthen"),
        ("Terraform", "learn"),
    ]
    assert "Python" not in [i["skill"] for i in roadmap["items"]]  # fully matched: no gap
    for item in roadmap["items"]:
        assert item["steps_source"] == "template"
        assert item["steps"] and item["project_idea"]
        assert item["youtube_url"] == youtube_search_url(item["skill"])
    strengthen = roadmap["items"][1]
    assert strengthen["resume_evidence"][0]["quote"] == "used GitHub Actions"
    assert any("never names CI/CD" in s for s in strengthen["steps"])


def test_ai_roadmap_uses_ai_steps_but_never_ai_links():
    provider = FakeProvider(
        {
            "items": [
                {
                    "skill": "kubernetes",
                    "steps": ["Learn pods", "Deploy with kubectl", " "],
                    "project_idea": "Run your API on minikube",
                },
                {"skill": "Rust", "steps": ["unrelated"], "project_idea": "x"},  # not a gap: ignored
            ]
        }
    )
    roadmap = build_roadmap(result(), provider, None)
    assert roadmap["source"] == "ai"
    by_skill = {i["skill"]: i for i in roadmap["items"]}
    assert by_skill["Kubernetes"]["steps"] == ["Learn pods", "Deploy with kubectl"]
    assert by_skill["Kubernetes"]["steps_source"] == "ai"
    assert by_skill["Terraform"]["steps_source"] == "template"
    assert "Rust" not in by_skill
    assert any("no plan for" in n for n in roadmap["notices"])
    assert all(i["youtube_url"].startswith("https://www.youtube.com/results?search_query=") for i in roadmap["items"])
    prompt = provider.calls[0]["prompt"]
    assert "Kubernetes" in prompt and "Python" in prompt  # gaps + verified known skills


def test_ai_failure_falls_back_to_templates():
    roadmap = build_roadmap(result(), FakeProvider(error=AIError("503 UNAVAILABLE: busy")), None)
    assert roadmap["source"] == "fallback"
    assert roadmap["fallback_reason"] == "provider_error"
    assert "503" in roadmap["notices"][0]


def test_no_gaps_means_empty_roadmap_without_calling_ai():
    provider = FakeProvider()
    roadmap = build_roadmap({"matched": [], "missing": []}, provider, None)
    assert roadmap["items"] == []
    assert provider.calls == []
