"""Deterministic skill extraction against the curated taxonomy in data/skills.json.

Each mention found carries the exact surface text and a quote copied from the
input, so every quote is guaranteed to be a substring of the text it came from.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SKILLS_PATH = Path(__file__).resolve().parent / "data" / "skills.json"

MAX_QUOTE_CHARS = 220
# A term must not touch another letter/digit/underscore on either side, so
# "Java" is not found inside "JavaScript" and "SQL" is not found inside "MySQL".
_LEFT = r"(?<![A-Za-z0-9_])"
_RIGHT = r"(?![A-Za-z0-9_])"
# Text inside links and email addresses is never counted as skill evidence:
# "github.com/jane" is a link, not proof of GitHub experience.
# Bare domains count only with a path (site.com/me) or as a known profile host,
# so tech names like "ASP.NET" are not mistaken for links.
URL_OR_EMAIL = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|\S+@\S+\.\S+"
    r"|\b[\w-]+(?:\.[\w-]+)*\.(?:com|io|dev|org|net|in|ai|me)/\S*"
    r"|\b(?:github|gitlab|bitbucket|linkedin|stackoverflow)\.(?:com|io)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    terms: tuple[str, ...]
    terms_case_sensitive: tuple[str, ...]


@dataclass(frozen=True)
class Mention:
    skill: str
    term: str  # the surface text exactly as it appears in the input
    start: int
    end: int
    quote: str  # the line (or a window of it) containing the mention
    term_offset: int  # where `term` starts inside `quote`


def _term_pattern(term: str) -> str:
    # Any run of whitespace in a multi-word term matches any whitespace, so
    # "machine learning" still matches across a PDF line break.
    words = [re.escape(w) for w in term.split()]
    return _LEFT + r"\s+".join(words) + _RIGHT


@lru_cache(maxsize=1)
def load_taxonomy() -> tuple[Skill, ...]:
    data = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    return tuple(
        Skill(
            name=s["name"],
            category=s["category"],
            terms=tuple(s.get("terms", [])),
            terms_case_sensitive=tuple(s.get("terms_case_sensitive", [])),
        )
        for s in data["skills"]
    )


@lru_cache(maxsize=1)
def _compiled() -> tuple[tuple[re.Pattern, str], ...]:
    patterns = []
    for skill in load_taxonomy():
        for term in skill.terms:
            patterns.append((re.compile(_term_pattern(term), re.IGNORECASE), skill.name))
        for term in skill.terms_case_sensitive:
            patterns.append((re.compile(_term_pattern(term)), skill.name))
    return tuple(patterns)


@lru_cache(maxsize=1)
def skill_index() -> dict[str, Skill]:
    return {s.name: s for s in load_taxonomy()}


def quote_for(text: str, start: int, end: int) -> tuple[str, int]:
    """Return the line around [start, end) (trimmed to a window if long) and the
    offset of the mention inside it. The quote is always a verbatim substring of `text`.
    """
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    lo, hi = line_start, line_end
    if hi - lo > MAX_QUOTE_CHARS:
        half = max((MAX_QUOTE_CHARS - (end - start)) // 2, 0)
        lo = max(line_start, start - half)
        hi = min(line_end, lo + MAX_QUOTE_CHARS)
        lo = max(line_start, min(lo, hi - MAX_QUOTE_CHARS))
    # Trim surrounding whitespace without losing track of the offset.
    while lo < start and text[lo].isspace():
        lo += 1
    while hi > end and text[hi - 1].isspace():
        hi -= 1
    return text[lo:hi], start - lo


def find_mentions(text: str) -> list[Mention]:
    """Find every taxonomy mention in `text`, longest match first, no overlaps."""
    candidates = []
    for pattern, skill_name in _compiled():
        for m in pattern.finditer(text):
            candidates.append((m.start(), m.end(), skill_name))

    # Longer matches claim their span first: "React Native" beats "React",
    # "SQL Server" beats "SQL".
    candidates.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    taken: list[tuple[int, int]] = [m.span() for m in URL_OR_EMAIL.finditer(text)]
    accepted = []
    for start, end, skill_name in candidates:
        if any(start < t_end and end > t_start for t_start, t_end in taken):
            continue
        taken.append((start, end))
        accepted.append((start, end, skill_name))

    accepted.sort()
    mentions = []
    for s, e, name in accepted:
        quote, offset = quote_for(text, s, e)
        mentions.append(Mention(skill=name, term=text[s:e], start=s, end=e, quote=quote, term_offset=offset))
    return mentions


def group_by_skill(mentions: list[Mention]) -> dict[str, list[Mention]]:
    grouped: dict[str, list[Mention]] = {}
    for mention in mentions:
        grouped.setdefault(mention.skill, []).append(mention)
    return grouped
