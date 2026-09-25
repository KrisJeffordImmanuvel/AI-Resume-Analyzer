from datetime import date
from pathlib import Path

import pytest

from analysis_service import run_analysis
from career import build_timeline, career_view, load_roles, parse_dates, role_jd
from parsing import normalize_text
from skills import find_mentions, skill_index
from tests.conftest import FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
RESUME = normalize_text((SAMPLES / "sample_resume.txt").read_text(encoding="utf-8"))
JD = normalize_text((SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8"))
TODAY = date(2026, 9, 24)


def fallback_result():
    return run_analysis(RESUME, JD, provider=None, fallback_reason="no_api_key", embedder=None, semantic_threshold=0.6)


def test_role_profiles_use_real_skill_names_and_render_back_to_themselves():
    index = skill_index()
    roles = load_roles()
    assert len(roles) >= 8
    assert len({r["id"] for r in roles}) == len(roles)
    for role in roles:
        skills = role["required"] + role["preferred"]
        assert all(s in index for s in skills), role["id"]
        # The synthetic JD must be read by the engine as exactly these skills.
        assert {m.skill for m in find_mentions(role_jd(role))} == set(skills), role["id"]


def test_role_fit_uses_the_same_engine_and_ranks_sensibly():
    view = career_view(RESUME, fallback_result(), TODAY)
    fits = {f["id"]: f for f in view["roles"]}
    assert fits["backend"]["score"] == max(f["score"] for f in view["roles"])
    assert fits["backend"]["required_matched"] == fits["backend"]["required_total"]
    assert fits["product_manager"]["score"] < fits["backend"]["score"]
    assert "Node.js" in fits["fullstack"]["missing_required"]
    assert "Kubernetes" in fits["devops"]["missing_required"]


def test_verified_ai_skills_count_towards_role_fit():
    provider = FakeProvider(
        {
            "skills": [{"name": "CI/CD", "quote": "deployed them to AWS using GitHub Actions"}],
            "experience": [],
            "education": [],
        }
    )
    ai_result = run_analysis(RESUME, JD, provider=provider, fallback_reason=None, embedder=None, semantic_threshold=0.6)
    with_ai = {f["id"]: f for f in career_view(RESUME, ai_result, TODAY)["roles"]}
    without = {f["id"]: f for f in career_view(RESUME, fallback_result(), TODAY)["roles"]}
    assert with_ai["devops"]["required_related"] == 1
    assert with_ai["devops"]["score"] > without["devops"]["score"]


@pytest.mark.parametrize(
    "text, start, end, current",
    [
        ("Jan 2020 – Mar 2022", (2020, 1), (2022, 3), False),
        ("2022 - Present", (2022, 1), (2026, 9), True),
        ("Sept 2021 to 2023", (2021, 9), (2023, 12), False),
        ("2020", (2020, 1), (2020, 12), False),
    ],
)
def test_parse_dates(text, start, end, current):
    parsed = parse_dates(text, TODAY)
    assert (parsed["start"], parsed["end"], parsed["current"]) == (start, end, current)


def test_backwards_or_missing_dates_are_not_guessed():
    assert parse_dates("2023 - 2021", TODAY) is None  # a backwards range is not reinterpreted
    assert parse_dates("Lead Engineer, Acme", TODAY) is None


def ev(quote):
    return {"quote": quote, "term": None, "term_offset": None, "similarity": None}


def test_timeline_orders_items_measures_durations_and_flags_gaps():
    profile = {
        "experience": [
            {"title": "Engineer", "organization": "B", "dates": "Jun 2023 - Present", "evidence": ev("Engineer, B")},
            {"title": "Analyst", "organization": "A", "dates": "Jan 2019 - Dec 2021", "evidence": ev("Analyst, A")},
            {"title": "Intern", "organization": None, "dates": None, "evidence": ev("Intern somewhere")},
        ],
        "education": [{"qualification": "BSc", "institution": "U", "dates": "2018", "evidence": ev("BSc, U, 2018")}],
    }
    t = build_timeline(profile, TODAY)
    assert [(i["kind"], i["start"]) for i in t["items"]] == [
        ("education", "2018-01"),
        ("role", "2019-01"),
        ("role", "2023-06"),
    ]
    assert t["items"][1]["duration_months"] == 36
    assert t["items"][2]["current"] and t["items"][2]["end"] == "2026-09"
    assert t["items"][0]["duration_months"] is None  # a single year is a point, not a span
    assert t["gaps"] == [
        {"after": "Analyst, A", "before": "Engineer, B", "from": "2021-12", "to": "2023-06", "months": 17}
    ]
    assert t["career_span_months"] == 93
    assert any("no readable dates" in n for n in t["notices"])


def test_sample_timeline_from_fallback_profile():
    t = career_view(RESUME, fallback_result(), TODAY)["timeline"]
    assert t["roles"] == 2
    assert [i["evidence"]["quote"] for i in t["items"] if i["kind"] == "role"] == [
        "Junior Developer, Sample Retail Co (2020 - 2022)",
        "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)",
    ]
    assert all(i["evidence"]["quote"] in RESUME for i in t["items"])
    assert any("approximate" in n for n in t["notices"])
