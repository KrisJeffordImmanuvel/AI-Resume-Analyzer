import sys

import pytest

from semantic import EmbedderUnavailable, SentenceTransformerEmbedder, best_matches, resume_units
from tests.conftest import FakeEmbedder

RESUME = (
    "Priya Raman | https://github.com/example\n"
    "- Containerized services with Docker and deployed them using GitHub Actions.\n"
    "- Mentored two junior engineers.\n"
    "Python"
)


def test_units_are_verbatim_lines_with_enough_words():
    units = resume_units(RESUME)
    assert units == [
        "- Containerized services with Docker and deployed them using GitHub Actions.",
        "- Mentored two junior engineers.",
    ]
    assert all(u in RESUME for u in units)


def test_long_lines_are_split_into_sentences():
    line = ("Built a payments platform. " * 12).strip()
    units = resume_units(line)
    assert units == ["Built a payments platform."]


def test_best_match_above_threshold_is_returned_with_similarity():
    embedder = FakeEmbedder({"CI/CD": [1, 0], "GitHub Actions": [0.8, 0.6]})
    found = best_matches(["CI/CD", "Kubernetes"], RESUME, embedder, threshold=0.6)
    assert found == {"CI/CD": ("- Containerized services with Docker and deployed them using GitHub Actions.", 0.8)}


def test_matches_below_threshold_are_ignored():
    embedder = FakeEmbedder({"CI/CD": [1, 0], "GitHub Actions": [0.8, 0.6]})
    assert best_matches(["CI/CD"], RESUME, embedder, threshold=0.9) == {}


def test_missing_library_reports_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    embedder = SentenceTransformerEmbedder("any-model")
    with pytest.raises(EmbedderUnavailable, match="not installed"):
        embedder.encode(["hello"])


def test_model_load_failure_reports_unavailable(monkeypatch):
    class Broken:
        def __init__(self, *a, **k):
            raise OSError("no internet")

    fake_module = type(sys)("sentence_transformers")
    fake_module.SentenceTransformer = Broken
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    with pytest.raises(EmbedderUnavailable, match="download"):
        SentenceTransformerEmbedder("any-model").encode(["hello"])


def test_queries_include_alternative_names_from_the_skill_list():
    from semantic import skill_query

    assert skill_query("CI/CD") == (
        "Experience with CI/CD (cicd, continuous integration, continuous delivery, continuous deployment)"
    )
    assert skill_query("Agile") == "Experience with Agile"
    assert skill_query("Not In List") == "Experience with Not In List"
