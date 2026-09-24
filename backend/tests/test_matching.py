from pathlib import Path

import pytest

from matching import SCORE_LABEL, analyze, classify_jd_lines

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def priorities(jd):
    lines = jd.split("\n")
    return [(lines[i], info.priority) for i, info in enumerate(classify_jd_lines(jd))]


def test_priority_follows_section_headings():
    jd = "Requirements:\n- Python\nNice to have:\n- Docker\nResponsibilities:\n- Build APIs"
    assert priorities(jd) == [
        ("Requirements:", "required"),
        ("- Python", "required"),
        ("Nice to have:", "preferred"),
        ("- Docker", "preferred"),
        ("Responsibilities:", "standard"),
        ("- Build APIs", "standard"),
    ]


def test_preferred_qualifications_heading_is_preferred_not_required():
    assert priorities("Preferred Qualifications\n- Go")[1][1] == "preferred"


def test_inline_wording_overrides_the_section():
    jd = "Requirements:\n- Python\n- Kafka is a plus"
    assert priorities(jd)[2][1] == "preferred"
    assert priorities("We use Python. Docker experience is required.")[0][1] == "required"


def test_bullet_lines_are_never_headings():
    # "- Python" is short with no punctuation but is a bullet, not a heading.
    jd = "Nice to have:\n- Python\n- Docker"
    assert [p for _, p in priorities(jd)] == ["preferred"] * 3


def test_score_is_priority_weighted():
    jd = "Requirements:\n- Python\n- Docker\nNice to have:\n- Kafka"
    result = analyze("I use Python and Kafka.", jd)
    # Python matched (required, 3) + Kafka matched (preferred, 1) out of 3 + 3 + 1.
    assert result["score"]["matched_weight"] == 4
    assert result["score"]["total_weight"] == 7
    assert result["score"]["value"] == round(100 * 4 / 7)
    assert result["score"]["label"] == SCORE_LABEL
    breakdown = {b["priority"]: b for b in result["score"]["breakdown"]}
    assert (breakdown["required"]["matched"], breakdown["required"]["total"]) == (1, 2)
    assert (breakdown["preferred"]["matched"], breakdown["preferred"]["total"]) == (1, 1)
    assert [m["skill"] for m in result["missing"]] == ["Docker"]


def test_skill_mentioned_twice_takes_its_highest_priority():
    jd = "Nice to have:\n- Python\nRequirements:\n- Python"
    [missing] = analyze("nothing relevant", jd)["missing"]
    assert missing["priority"] == "required"


def test_exact_vs_literal_match_type():
    result = analyze("Built UIs in JS. Wrote Python.", "Need JavaScript and Python")
    types = {m["skill"]: m["match_type"] for m in result["matched"]}
    assert types == {"JavaScript": "literal", "Python": "exact"}


def test_no_jd_skills_means_no_score_and_a_warning():
    result = analyze("Python developer", "We are hiring a great teammate.")
    assert result["score"]["value"] is None
    assert result["warnings"]


def test_resume_only_skills_are_listed_as_additional():
    result = analyze("Python and Rust", "Need Python")
    assert [a["skill"] for a in result["additional"]] == ["Rust"]


def test_analysis_is_deterministic():
    resume, jd = "Python, Docker, AWS", "Requirements: Python, Kubernetes"
    assert analyze(resume, jd) == analyze(resume, jd)


@pytest.mark.parametrize("name", ["sample_resume.txt"])
def test_every_quote_is_verbatim_source_text(name):
    resume = (SAMPLES / name).read_text(encoding="utf-8")
    jd = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")
    result = analyze(resume, jd)
    assert result["matched"] and result["missing"]
    for item in result["matched"] + result["additional"]:
        for ev in item["resume_evidence"]:
            assert ev["quote"] in resume
            assert ev["quote"][ev["term_offset"]:].startswith(ev["term"])
    for item in result["matched"] + result["missing"]:
        for ev in item["jd_evidence"]:
            assert ev["quote"] in jd
            assert ev["quote"][ev["term_offset"]:].startswith(ev["term"])
