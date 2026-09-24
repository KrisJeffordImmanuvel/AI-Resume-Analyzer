"""Deterministic JD↔resume matching and priority-weighted job-fit scoring.

This is the single analysis engine. Job Seeker and (later) Job Provider flows
both call analyze(); there is no other scoring path.
"""

import re
from dataclasses import dataclass

from skills import Mention, find_mentions, group_by_skill, skill_index

SCORE_LABEL = "Application-generated estimate, not an official ATS or hiring decision."
MAX_QUOTES_PER_SKILL = 3

PRIORITY_WEIGHTS = {"required": 3, "standard": 2, "preferred": 1}
_PRIORITY_RANK = {"preferred": 0, "standard": 1, "required": 2}

# Checked before the required keywords: "Preferred qualifications" is preferred,
# even though "qualifications" alone would read as required.
_PREFERRED_WORDS = re.compile(
    r"\b(preferred|nice[\s-]to[\s-]have|good[\s-]to[\s-]have|bonus|desirable|a plus|is a plus|are a plus|"
    r"plus points?|optional|familiarity with|exposure to)\b",
    re.IGNORECASE,
)
_REQUIRED_WORDS = re.compile(
    r"\b(required|requirements?|must[\s-]haves?|must|mandatory|essential|minimum qualifications|"
    r"basic qualifications|qualifications|what you(?:'|’)ll need|what we(?:'|’)re looking for|you have)\b",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^\s*([-*•·▪◦‣–]|\d+[.)])\s+")


@dataclass
class _LineInfo:
    start: int
    end: int
    priority: str


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or _BULLET.match(line):
        return False
    core = stripped.lstrip("#").strip().rstrip(":").strip()
    if not core or len(core.split()) > 6 or re.search(r"[.!?,;]$", core):
        return False
    return stripped.endswith(":") or stripped.startswith("#") or bool(
        _PREFERRED_WORDS.search(core) or _REQUIRED_WORDS.search(core)
    )


def classify_jd_lines(jd_text: str) -> list[_LineInfo]:
    """Assign each JD line a priority from its section heading and its own wording."""
    infos = []
    section = "standard"
    offset = 0
    for line in jd_text.split("\n"):
        start, end = offset, offset + len(line)
        offset = end + 1
        if _is_heading(line):
            if _PREFERRED_WORDS.search(line):
                section = "preferred"
            elif _REQUIRED_WORDS.search(line):
                section = "required"
            else:
                section = "standard"  # e.g. "Responsibilities:", "About us:"
            priority = section
        elif _PREFERRED_WORDS.search(line):
            priority = "preferred"
        elif _REQUIRED_WORDS.search(line):
            priority = "required"
        else:
            priority = section
        infos.append(_LineInfo(start, end, priority))
    return infos


def _priority_at(infos: list[_LineInfo], pos: int) -> str:
    for info in infos:
        if info.start <= pos <= info.end:
            return info.priority
    return "standard"


def _evidence(mentions: list[Mention]) -> list[dict]:
    out, seen = [], set()
    for m in mentions:
        if m.quote in seen:
            continue
        seen.add(m.quote)
        out.append({"quote": m.quote, "term": m.term, "term_offset": m.term_offset})
        if len(out) == MAX_QUOTES_PER_SKILL:
            break
    return out


def analyze(resume_text: str, jd_text: str) -> dict:
    """Compare a resume to a JD. Pure function: same input, same output."""
    index = skill_index()
    resume_skills = group_by_skill(find_mentions(resume_text))
    jd_skills = group_by_skill(find_mentions(jd_text))
    line_infos = classify_jd_lines(jd_text)

    matched, missing = [], []
    breakdown = {p: {"priority": p, "weight": w, "matched": 0, "total": 0} for p, w in PRIORITY_WEIGHTS.items()}
    matched_weight = total_weight = 0

    for name, jd_mentions in jd_skills.items():
        priority = max(
            (_priority_at(line_infos, m.start) for m in jd_mentions), key=_PRIORITY_RANK.__getitem__
        )
        weight = PRIORITY_WEIGHTS[priority]
        total_weight += weight
        breakdown[priority]["total"] += 1
        base = {
            "skill": name,
            "category": index[name].category,
            "priority": priority,
            "jd_evidence": _evidence(jd_mentions),
        }
        resume_mentions = resume_skills.get(name)
        if resume_mentions:
            jd_terms = {m.term.lower() for m in jd_mentions}
            same_wording = any(m.term.lower() in jd_terms for m in resume_mentions)
            matched_weight += weight
            breakdown[priority]["matched"] += 1
            matched.append({
                **base,
                "match_type": "exact" if same_wording else "literal",
                "resume_evidence": _evidence(resume_mentions),
            })
        else:
            missing.append(base)

    additional = [
        {"skill": name, "category": index[name].category, "resume_evidence": _evidence(mentions)}
        for name, mentions in resume_skills.items()
        if name not in jd_skills
    ]

    order = lambda item: (-_PRIORITY_RANK[item["priority"]], item["skill"].lower())  # noqa: E731
    matched.sort(key=order)
    missing.sort(key=order)
    additional.sort(key=lambda item: (item["category"], item["skill"].lower()))

    warnings = []
    if not jd_skills:
        warnings.append(
            "No recognizable skills were found in the job description, so no score was calculated."
        )
    if not resume_skills:
        warnings.append("No recognizable skills were found in the resume.")

    value = round(100 * matched_weight / total_weight) if total_weight else None
    return {
        "method": "deterministic",
        "score": {
            "value": value,
            "label": SCORE_LABEL,
            "matched_weight": matched_weight,
            "total_weight": total_weight,
            "breakdown": [breakdown[p] for p in ("required", "standard", "preferred")],
        },
        "matched": matched,
        "missing": missing,
        "additional": additional,
        "warnings": warnings,
    }
