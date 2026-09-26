"""Verification of quotes that come from outside the deterministic engine (e.g. AI).

A quote is accepted only if it can be found in the source text. The quote that
is kept is always copied from the source, never the AI's own wording.
"""

import re
import unicodedata

MIN_QUOTE_CHARS = 3
MAX_QUOTE_CHARS = 400

# AI output often "tidies" punctuation; treat these as equivalent when locating.
_EQUIVALENT = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        "•": "•",
    }
)


def _canon(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(_EQUIVALENT)


def locate_quote(source: str, quote: str) -> tuple[int, int] | None:
    """Find `quote` in `source`, allowing only whitespace and punctuation-style differences.

    Returns the (start, end) span in `source`, or None if the quote is not there.
    """
    quote = (quote or "").strip()
    if not (MIN_QUOTE_CHARS <= len(quote) <= MAX_QUOTE_CHARS):
        return None
    canon_source = _canon(source)
    canon_quote = _canon(quote)
    # _canon maps each character to exactly one character, so offsets line up.
    if len(canon_source) != len(source):
        canon_source = source
        canon_quote = quote
    index = canon_source.find(canon_quote)
    if index != -1:
        return index, index + len(canon_quote)
    words = canon_quote.split()
    pattern = r"\s+".join(re.escape(w) for w in words)
    match = re.search(pattern, canon_source)
    return match.span() if match else None


def verified_quote(source: str, quote: str) -> str | None:
    """Return the verbatim source text for `quote`, or None if it is not in `source`."""
    span = locate_quote(source, quote)
    return source[span[0] : span[1]] if span else None


def _loose(text: str) -> str:
    return " ".join(_canon(text).lower().split())


def value_in(value: str | None, text: str) -> bool:
    """True if `value` appears in `text`, ignoring case, spacing and dash/quote style."""
    return bool(value) and _loose(value) in _loose(text)


def find_term(quote: str, term: str) -> int | None:
    """Offset of `term` in `quote` (case-insensitive), or None."""
    index = _canon(quote).lower().find(_canon(term).lower())
    return index if index != -1 else None
