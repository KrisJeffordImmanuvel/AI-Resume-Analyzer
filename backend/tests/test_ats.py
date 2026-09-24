from pathlib import Path

from ats import _has_phone, ats_view, keyword_diff, parse_preview
from parsing import normalize_text

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
RESUME = normalize_text((SAMPLES / "sample_resume.txt").read_text(encoding="utf-8"))
JD = normalize_text((SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8"))


def test_parse_preview_shows_exact_text_and_finds_structure():
    p = parse_preview(RESUME)
    assert p["text"] == RESUME
    assert p["headings"] == ["Summary", "Experience", "Skills", "Education"]
    assert p["contact"] == {"email": True, "phone": False, "linkedin": False, "github": True}
    assert p["issues"] == ["No phone number was found in the extracted text."]


def test_parse_preview_flags_thin_text_and_missing_headings():
    issues = " ".join(parse_preview("Jane Doe\njane@example.com")["issues"])
    assert "Very little text" in issues
    assert "Experience" in issues and "Skills" in issues


def test_phone_detection_ignores_date_ranges():
    assert _has_phone("+91 98765 43210")
    assert _has_phone("(555) 123-4567")
    assert not _has_phone("2020 - 2022")


def test_keyword_diff_distinguishes_exact_wording_from_same_skill():
    diff = keyword_diff(RESUME, JD)
    rows = {r["keyword"]: r for r in diff["keywords"]}
    js = rows["JavaScript"]  # resume says "JS"
    assert (js["exact_in_resume"], js["skill_in_resume"]) == (False, True)
    assert rows["Python"]["exact_in_resume"] is True
    assert rows["Kubernetes"]["skill_in_resume"] is False
    assert diff["summary"]["different_wording"] == 1
    terms = [r["keyword"] for r in diff["keywords"] if r["kind"] == "term"]
    assert "payments" in terms  # from the JD title
    assert "occasional" not in terms  # one-off filler word


def test_six_second_scan_checks():
    view = ats_view(RESUME, JD, {"experience": [{"evidence": {"quote": "Software Engineer, Example Fintech"}}]})
    checks = {c["label"]: c for c in view["scan"]["checks"]}
    assert checks["Job's skills visible near the top"]["passed"]
    assert checks["Most recent role easy to find"]["detail"] == "Software Engineer, Example Fintech"
    assert checks["Achievements have numbers"]["detail"] == "4 of 7 bullets include a number."
    assert "heuristic" in view["label"]


def test_recent_role_falls_back_to_first_dated_line_when_profile_is_empty():
    checks = {c["label"]: c for c in ats_view(RESUME, JD, {"experience": []})["scan"]["checks"]}
    assert checks["Most recent role easy to find"]["passed"]
    assert checks["Most recent role easy to find"]["detail"] == (
        "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)")
