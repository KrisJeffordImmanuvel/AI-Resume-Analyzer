from pathlib import Path

from ai_provider import AIError
from interview import build_feedback, build_questions, fallback_questions, rule_based_feedback
from matching import analyze
from parsing import normalize_text
from tests.conftest import FakeProvider

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
RESUME = normalize_text((SAMPLES / "sample_resume.txt").read_text(encoding="utf-8"))
JD = normalize_text((SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8"))
RESULT = {
    **analyze(RESUME, JD),
    "profile": {
        "experience": [
            {
                "title": None,
                "organization": None,
                "dates": "2022 - Present",
                "evidence": {
                    "quote": "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)",
                    "term": None,
                    "term_offset": None,
                    "similarity": None,
                },
            }
        ]
    },
}


def test_fallback_questions_are_grounded_in_verbatim_text():
    questions = fallback_questions(RESULT)
    types = [q["type"] for q in questions]
    assert types.count("skill") == 3 and types.count("gap") == 2
    assert types.count("experience") == 1 and types.count("behavioral") == 2
    for q in questions:
        if q["type"] == "behavioral":
            assert q["grounding"] is None
        else:
            source_text = RESUME if q["grounding"]["source"] == "resume" else JD
            assert q["grounding"]["quote"] in source_text


def test_ai_questions_without_verified_grounding_are_discarded():
    provider = FakeProvider(
        {
            "questions": [
                {
                    "type": "skill",
                    "skill": "Redis",
                    "question": "How did Redis caching cut report time by 60%?",
                    "based_on_quote": "Cut report generation time by 60% by adding Redis caching.",
                },
                {
                    "type": "gap",
                    "skill": "Kubernetes",
                    "question": "How would you learn Kubernetes quickly?",
                    "based_on_quote": "Experience with Docker and Kubernetes.",
                },
                {
                    "type": "experience",
                    "skill": None,
                    "question": "Tell me about your time at Google.",
                    "based_on_quote": "Senior Engineer, Google (2018 - 2020)",
                },  # invented premise
                {"type": "skill", "skill": "Go", "question": "Explain goroutines you wrote.", "based_on_quote": None},
                {
                    "type": "behavioral",
                    "skill": None,
                    "question": "Tell me about a hard deadline you met.",
                    "based_on_quote": None,
                },
                {"type": "trivia", "skill": None, "question": "What is 2 + 2 in binary?", "based_on_quote": None},
            ]
        }
    )
    questions, sources = build_questions(RESUME, JD, RESULT, provider, None)
    assert sources["source"] == "ai"
    assert [q["question"][:20] for q in questions] == [
        "How did Redis cachin",
        "How would you learn ",
        "Tell me about a hard",
    ]
    assert questions[0]["grounding"] == {
        "source": "resume",
        "quote": "Cut report generation time by 60% by adding Redis caching.",
    }
    assert questions[1]["grounding"]["source"] == "jd"
    assert "3 AI question(s) were discarded" in sources["notices"][0]


def test_ai_question_failure_falls_back():
    questions, sources = build_questions(RESUME, JD, RESULT, FakeProvider(error=AIError("boom")), None)
    assert sources["source"] == "fallback"
    assert sources["fallback_reason"] == "provider_error"
    assert questions == fallback_questions(RESULT)


def test_ai_returning_only_bad_questions_falls_back():
    provider = FakeProvider(
        {
            "questions": [
                {
                    "type": "skill",
                    "skill": "X",
                    "question": "Invented premise?",
                    "based_on_quote": "not in any document",
                }
            ]
        }
    )
    questions, sources = build_questions(RESUME, JD, RESULT, provider, None)
    assert sources["source"] == "fallback"
    assert questions == fallback_questions(RESULT)


STRONG = (
    "At my last job our nightly report took four hours. I profiled the queries and I designed a Redis cache "
    "for the slowest aggregates, then wrote tests around the cache invalidation. The result was that report "
    "time dropped by 60%, from 4 hours to about 95 minutes, and the finance team got numbers before 9am. "
    "I also documented the approach so two teammates could extend it to other reports without my help, "
    "which later saved another hour on the weekly export."
)


def test_rule_based_feedback_recognises_a_strong_answer():
    fb = rule_based_feedback({"skill": "Redis", "question": "q"}, STRONG)
    assert fb["rating"] is None
    points = [p["point"] for p in fb["strengths"]]
    assert "Describes what you did yourself." in points
    assert "Uses concrete numbers." in points
    assert "States an outcome." in points
    assert "Connects the answer to Redis." in points
    assert fb["improvements"] == []
    for p in fb["strengths"]:
        if p["answer_quote"]:
            assert p["answer_quote"] in STRONG


def test_rule_based_feedback_flags_a_weak_answer():
    fb = rule_based_feedback({"skill": "Kubernetes", "question": "q"}, "We worked on the platform as a team.")
    text = " ".join(p["point"] for p in fb["improvements"])
    assert "Too short" in text
    assert "personally" in text
    assert "concrete number" in text
    assert "result" in text
    assert "never mentions it" in text
    assert fb["follow_up_question"].startswith("What measurable result")


def test_ai_feedback_keeps_only_verified_answer_quotes():
    provider = FakeProvider(
        {
            "rating": 4,
            "summary": "Clear and specific.",
            "strengths": [
                {"point": "Quantified impact", "answer_quote": "report time dropped by 60%"},
                {"point": "Owned the work", "answer_quote": "I single-handedly rebuilt the platform"},
            ],
            "improvements": [{"point": "Mention trade-offs", "answer_quote": None}],
            "follow_up_question": "How did you handle cache invalidation bugs?",
        }
    )
    fb = build_feedback({"skill": "Redis", "question": "q"}, STRONG, provider, None)
    assert fb["source"] == "ai" and fb["rating"] == 4
    assert fb["strengths"][0]["answer_quote"] == "report time dropped by 60%"
    assert fb["strengths"][1]["answer_quote"] is None  # not in the answer: quote removed
    assert fb["follow_up_question"].endswith("?")


def test_ai_feedback_out_of_range_rating_is_dropped():
    provider = FakeProvider(
        {"rating": 9, "summary": "s", "strengths": [{"point": "p"}], "improvements": [], "follow_up_question": "f?"}
    )
    assert build_feedback({"question": "q"}, STRONG, provider, None)["rating"] is None


def test_ai_feedback_failure_falls_back_to_rules():
    fb = build_feedback({"skill": None, "question": "q"}, STRONG, FakeProvider(error=AIError("429")), None)
    assert fb["source"] == "fallback" and fb["fallback_reason"] == "provider_error"
    assert fb["rating"] is None
    assert "429" in fb["notices"][0]
