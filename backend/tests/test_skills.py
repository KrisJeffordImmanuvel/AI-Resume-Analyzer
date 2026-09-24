import pytest

from skills import find_mentions, load_taxonomy, quote_for


def names(text):
    return [m.skill for m in find_mentions(text)]


def test_taxonomy_is_curated_and_consistent():
    skills = load_taxonomy()
    assert len(skills) >= 300
    assert len({s.name for s in skills}) == len(skills)
    seen = {}
    for s in skills:
        assert s.terms or s.terms_case_sensitive, s.name
        for term in s.terms:
            assert term == term.lower(), f"{s.name}: case-insensitive terms must be lowercase"
            assert term not in seen, f"{term!r} used by {s.name} and {seen.get(term)}"
            seen[term] = s.name


@pytest.mark.parametrize(
    "text, expected",
    [
        ("JavaScript", ["JavaScript"]),  # not also Java
        ("MySQL", ["MySQL"]),  # not also SQL
        ("React Native", ["React Native"]),  # longest match wins
        ("SQL Server", ["Microsoft SQL Server"]),
        ("C++ and C#", ["C++", "C#"]),
        ("ASP.NET", ["ASP.NET"]),
        ("machine\nlearning", ["Machine Learning"]),  # across a line break
        ("PYTHON", ["Python"]),  # case-insensitive terms
    ],
)
def test_term_boundaries_and_longest_match(text, expected):
    assert names(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Budget for R&D",  # bare "R" is not a skill term
        "They react to incidents quickly",  # lowercase "react" is a verb
        "I excel at planning",  # lowercase "excel"
        "the notion of ownership",
        "https://github.com/jane",
        "jane@gitlab.com",
        "linkedin.com/in/jane",
    ],
)
def test_ambiguous_words_and_links_are_not_skills(text):
    assert names(text) == []


def test_case_sensitive_terms_still_match_proper_nouns():
    assert names("Built dashboards in React and Excel") == ["React", "Excel"]


def test_mentions_keep_exact_surface_text():
    [m] = find_mentions("Wrote services in NodeJS")
    assert m.skill == "Node.js"
    assert m.term == "NodeJS"


def test_quote_is_the_containing_line_and_a_substring():
    text = "Header\n- Built APIs with Python and Docker\nFooter"
    for m in find_mentions(text):
        assert m.quote == "- Built APIs with Python and Docker"
        assert m.quote in text


def test_long_lines_are_trimmed_to_a_window_that_contains_the_term():
    text = ("filler " * 100) + "Kubernetes" + (" filler" * 100)
    [m] = find_mentions(text)
    assert "Kubernetes" in m.quote
    assert len(m.quote) <= 220
    assert m.quote in text
    assert quote_for(text, m.start, m.end) == (m.quote, m.term_offset)


def test_term_offset_points_at_the_matched_occurrence():
    # "SQL" also appears inside "PostgreSQL"; the offset must point at the standalone one.
    text = "  - Strong knowledge of PostgreSQL and SQL.  "
    by_skill = {m.skill: m for m in find_mentions(text)}
    sql = by_skill["SQL"]
    assert sql.quote == "- Strong knowledge of PostgreSQL and SQL."
    assert sql.quote[sql.term_offset:].startswith("SQL.")
    assert sql.quote.index("SQL") != sql.term_offset
