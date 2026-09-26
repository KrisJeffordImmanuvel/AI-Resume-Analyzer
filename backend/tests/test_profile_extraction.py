from pathlib import Path

from ai_provider import AIError
from profile_extraction import SYSTEM_PROMPT, AIResumeProfile, extract_profile
from tests.conftest import FakeProvider

RESUME = (Path(__file__).resolve().parents[2] / "samples" / "sample_resume.txt").read_text(encoding="utf-8")
from parsing import normalize_text  # noqa: E402

RESUME = normalize_text(RESUME)


def ai_response(**overrides):
    base = {
        "skills": [
            {"name": "Python", "quote": "REST APIs and data pipelines in Python"},
            {"name": "CI/CD", "quote": "deployed them to AWS using GitHub Actions"},
            {"name": "Kubernetes", "quote": "Orchestrated clusters with Kubernetes"},  # fabricated
        ],
        "experience": [
            {
                "title": "Software Engineer",
                "organization": "Example Fintech Pvt Ltd",
                "dates": "2022 – Present",
                "quote": "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)",
            },
            {
                "title": "Staff Engineer",  # not in its quote -> discarded
                "organization": "Sample Retail Co",
                "dates": None,
                "quote": "Junior Developer, Sample Retail Co (2020 - 2022)",
            },
            {
                "title": "Junior Developer",
                "organization": "Google",  # not in the quote -> field removed
                "dates": "2019 - 2021",  # not in the quote -> field removed
                "quote": "Junior Developer, Sample Retail Co (2020 - 2022)",
            },
        ],
        "education": [
            {
                "qualification": "B.E. Computer Science",
                "institution": "Example Institute of Technology",
                "dates": "2020",
                "quote": "B.E. Computer Science, Example Institute of Technology, 2020",
            }
        ],
    }
    base.update(overrides)
    return base


def test_ai_profile_keeps_only_verified_items_and_fields():
    provider = FakeProvider(ai_response())
    profile = extract_profile(RESUME, provider, None)

    assert profile["source"] == "ai"
    assert profile["model"] == "fake:fake-model"
    assert [s["name"] for s in profile["skills"]] == ["Python", "CI/CD"]
    assert profile["discarded"] == 2  # fabricated Kubernetes skill + Staff Engineer

    first, second = profile["experience"]
    assert (first["title"], first["organization"], first["dates"]) == (
        "Software Engineer",
        "Example Fintech Pvt Ltd",
        "2022 – Present",
    )
    assert (second["title"], second["organization"], second["dates"]) == ("Junior Developer", None, None)
    [edu] = profile["education"]
    assert edu["institution"] == "Example Institute of Technology"


def test_every_kept_ai_quote_is_verbatim_resume_text():
    profile = extract_profile(RESUME, FakeProvider(ai_response()), None)
    items = profile["skills"] + profile["experience"] + profile["education"]
    for item in items:
        ev = item["evidence"]
        assert ev["quote"] in RESUME
        if ev["term"] is not None:
            assert ev["quote"][ev["term_offset"] :].startswith(ev["term"])


def test_ai_skills_are_mapped_to_the_taxonomy():
    profile = extract_profile(RESUME, FakeProvider(ai_response()), None)
    mapped = {s["name"]: s["mapped_skill"] for s in profile["skills"]}
    assert mapped == {"Python": "Python", "CI/CD": "CI/CD"}


def test_prompt_sends_resume_as_data_with_strict_rules():
    provider = FakeProvider(ai_response())
    extract_profile(RESUME, provider, None)
    [call] = provider.calls
    assert RESUME in call["prompt"]
    assert call["system"] == SYSTEM_PROMPT
    assert "never guess" in SYSTEM_PROMPT.lower()
    assert call["schema"] is AIResumeProfile


def test_provider_error_falls_back_with_a_notice():
    profile = extract_profile(RESUME, FakeProvider(error=AIError("quota exceeded")), None)
    assert profile["source"] == "fallback"
    assert profile["fallback_reason"] == "provider_error"
    assert "quota exceeded" in profile["notices"][0]


def test_no_provider_uses_fallback_with_given_reason():
    profile = extract_profile(RESUME, None, "no_api_key")
    assert profile["source"] == "fallback"
    assert profile["fallback_reason"] == "no_api_key"
    assert profile["notices"] == []


def test_fallback_detects_experience_and_education_by_pattern():
    profile = extract_profile(RESUME, None, "demo_mode")
    dates = [e["dates"] for e in profile["experience"]]
    assert dates == ["2022 - Present", "2020 - 2022"]
    assert all(e["title"] is None for e in profile["experience"])  # no guessing without AI
    [edu] = profile["education"]
    assert edu["dates"] == "2020"
    assert "B.E. Computer Science" in edu["evidence"]["quote"]
    assert "Python" in [s["name"] for s in profile["skills"]]
    for item in profile["skills"] + profile["experience"] + profile["education"]:
        assert item["evidence"]["quote"] in RESUME
