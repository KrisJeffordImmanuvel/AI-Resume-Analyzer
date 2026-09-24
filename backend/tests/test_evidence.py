import pytest

from evidence import find_term, locate_quote, value_in, verified_quote

SOURCE = "Software Engineer, Example Fintech Pvt Ltd (2022 - Present)\n- Built RESTful APIs with FastAPI."


def test_exact_quote_is_found():
    assert verified_quote(SOURCE, "Built RESTful APIs") == "Built RESTful APIs"


def test_quote_may_differ_only_in_whitespace_and_returns_source_text():
    quote = verified_quote(SOURCE, "Example Fintech Pvt Ltd (2022 - Present) - Built")
    assert quote == "Example Fintech Pvt Ltd (2022 - Present)\n- Built"
    assert quote in SOURCE


@pytest.mark.parametrize("ai_quote", ["(2022 – Present)", "(2022 — Present)"])
def test_dash_style_differences_are_tolerated(ai_quote):
    assert verified_quote(SOURCE, ai_quote) == "(2022 - Present)"


@pytest.mark.parametrize(
    "fabricated",
    ["Built GraphQL APIs", "Senior Engineer at Google", "", "ab", "x" * 401],
)
def test_fabricated_or_unusable_quotes_are_rejected(fabricated):
    assert locate_quote(SOURCE, fabricated) is None


def test_value_in_ignores_case_and_spacing():
    assert value_in("example  fintech", SOURCE)
    assert not value_in("Google", SOURCE)
    assert not value_in(None, SOURCE)


def test_find_term_is_case_insensitive():
    assert find_term("Built RESTful APIs", "restful") == 6
    assert find_term("Built RESTful APIs", "GraphQL") is None
