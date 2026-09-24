import pytest

from ai_provider import AIError
from resume_quality import (
    check_bullet, extract_bullets, quality_report, rewrite_bullet, rule_based_rewrite, verify_rewrite,
)
from tests.conftest import FakeProvider

RESUME = """Jane Doe
EXPERIENCE
- Cut report generation time by 60% by adding Redis caching.
- Responsible for building internal dashboards in React.
* Worked on the platform since 2021
1. Led a team of 4 engineers delivering a payments API.
Plain paragraph line that is not a bullet.
"""


def codes(bullet):
    return [i["code"] for i in check_bullet(bullet)["issues"]]


def test_bullets_are_extracted_verbatim():
    assert extract_bullets(RESUME) == [
        "- Cut report generation time by 60% by adding Redis caching.",
        "- Responsible for building internal dashboards in React.",
        "* Worked on the platform since 2021",
        "1. Led a team of 4 engineers delivering a payments API.",
    ]


def test_strong_quantified_bullet_has_no_issues():
    check = check_bullet("- Cut report generation time by 60% by adding Redis caching.")
    assert (check["verb"], check["quantified"], check["metric"], check["issues"]) == ("strong", True, "60%", [])


def test_weak_opener_and_missing_metric_are_flagged():
    assert codes("- Responsible for building internal dashboards in React.") == ["no_metric", "weak_opener"]


def test_years_do_not_count_as_metrics():
    check = check_bullet("* Worked on the platform since 2021")
    assert check["quantified"] is False
    assert "no_metric" in codes("* Worked on the platform since 2021")


@pytest.mark.parametrize("bullet, code", [
    ("- Built it", "too_short"),
    ("- Built " + "very " * 40 + "big things", "too_long"),
    ("- Built my first API with 3 endpoints", "first_person"),
    ("- Delivered various features for 2 teams as a team player", "filler"),
    ("- The API that served 2M requests", "no_action_verb"),
])
def test_individual_checks(bullet, code):
    assert code in codes(bullet)


def test_report_summary_counts():
    report = quality_report(RESUME)
    assert report["summary"] == {"bullets": 4, "quantified": 2, "strong_verb": 2, "with_issues": 2}
    assert quality_report("No bullets here.\nJust text.")["notices"]


def test_rule_based_rewrite_fixes_opener_and_adds_placeholder_not_facts():
    out = rule_based_rewrite("- Responsible for building internal dashboards in React.")
    assert out["text"] == "Built internal dashboards in React, [result: e.g. reduced X by N%]."
    assert out["placeholders"] == ["[result: e.g. reduced X by N%]"]
    assert rule_based_rewrite("* Worked on the platform since 2021")["text"].startswith("[Action verb] the platform")


def test_verify_rewrite_rejects_new_numbers_and_skills_but_allows_placeholders():
    bullet = "- Built dashboards in React for 3 teams"
    assert verify_rewrite("Built React dashboards for 3 teams, cutting reporting time by [X%]", bullet, "") is None
    assert "75" in verify_rewrite("Built React dashboards for 3 teams, cutting time by 75%", bullet, "")
    assert "Kubernetes" in verify_rewrite("Built React dashboards on Kubernetes for 3 teams", bullet, "")
    # A skill elsewhere in the resume is a known fact, not an invention.
    assert verify_rewrite("Built React and Redis-backed dashboards for 3 teams", bullet, "Redis caching") is None


def test_ai_rewrite_keeps_only_verified_variants():
    provider = FakeProvider({"variants": [
        {"text": "Built internal React dashboards used by [N users].", "note": "Stronger verb"},
        {"text": "Built internal React dashboards that cut reporting time by 40%.", "note": "Added metric"},
        {"text": "Built internal React dashboards deployed on AWS.", "note": "Added context"},
    ]})
    out = rewrite_bullet("- Responsible for building internal dashboards in React.", RESUME, provider, None)
    assert out["source"] == "ai"
    assert [v["text"] for v in out["variants"]] == ["Built internal React dashboards used by [N users]."]
    assert out["variants"][0]["placeholders"] == ["[N users]"]
    assert len(out["notices"]) == 2
    assert "40" in out["notices"][0] and "AWS" in out["notices"][1]
    assert out["check"]["verb"] == "weak"


def test_ai_rewrite_with_nothing_usable_falls_back():
    provider = FakeProvider({"variants": [{"text": "Built dashboards serving 10,000 users.", "note": "x"}]})
    out = rewrite_bullet("- Built dashboards", RESUME, provider, None)
    assert out["source"] == "fallback" and out["fallback_reason"] == "provider_error"
    assert "no-new-facts" in out["notices"][-1]


def test_ai_rewrite_failure_falls_back():
    out = rewrite_bullet("- Built dashboards", RESUME, FakeProvider(error=AIError("503 busy")), None)
    assert out["source"] == "fallback"
    assert "503 busy" in out["notices"][0]


def test_written_numbers_count_as_metrics():
    assert check_bullet("- Mentored two junior engineers and led weekly code reviews.")["metric"] == "two"
    assert check_bullet("- Doubled test coverage across the platform services")["quantified"]
