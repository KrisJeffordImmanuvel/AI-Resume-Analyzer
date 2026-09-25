"""Manual LinkedIn consistency check: compare pasted LinkedIn text with the resume.

No scraping: the user pastes text from their own profile. Both sides are turned
into profiles with the same extraction (AI with verified quotes, or the
pattern-based fallback), then roles, dates and skills are compared. Every
finding quotes both documents; this checks consistency, not truth.
"""

import re
from datetime import date

from ai_provider import AIProvider
from career import parse_dates
from parsing import clean_jd_text
from profile_extraction import extract_profile
from skills import find_mentions, group_by_skill

DATE_TOLERANCE_MONTHS = 2
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.&-]*")
_STOP = {
    "and",
    "the",
    "of",
    "at",
    "in",
    "for",
    "a",
    "an",
    "to",
    "present",
    "current",
    "now",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "full-time",
    "part-time",
    "yrs",
    "yr",
    "mos",
    "mo",
    "months",
    "years",
}


def _key_words(entry: dict) -> set[str]:
    text = " ".join(filter(None, [entry.get("title"), entry.get("organization")])) or entry["evidence"]["quote"]
    return {w.lower().strip(".,") for w in _WORD.findall(text) if w.lower().strip(".,") not in _STOP and len(w) > 1}


def _similarity(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _dates(entry: dict, today: date) -> dict | None:
    return parse_dates(entry.get("dates") or "", today) or parse_dates(entry["evidence"]["quote"], today)


def _months_apart(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs((a[0] - b[0]) * 12 + (a[1] - b[1]))


def _date_diff(r: dict | None, l: dict | None) -> str | None:
    if not r or not l:
        return None
    # Year-only dates can only be compared to the year.
    precise = r["month_precision"] and l["month_precision"]
    tol = DATE_TOLERANCE_MONTHS if precise else 11
    problems = []
    if _months_apart(r["start"], l["start"]) > tol:
        problems.append(f"start {r['text']} vs {l['text']}")
    elif r["current"] != l["current"]:
        problems.append("one says current, the other has an end date")
    elif not r["current"] and _months_apart(r["end"], l["end"]) > tol:
        problems.append(f"end {r['text']} vs {l['text']}")
    return "; ".join(problems) or None


def compare_roles(resume_roles: list[dict], linkedin_roles: list[dict], today: date) -> list[dict]:
    rows, used = [], set()
    for r in resume_roles:
        best, best_score = None, 0.0
        for i, l in enumerate(linkedin_roles):
            if i in used:
                continue
            score = _similarity(_key_words(r), _key_words(l))
            if score > best_score:
                best, best_score = i, score
        if best is not None and best_score >= 0.34:
            used.add(best)
            l = linkedin_roles[best]
            diff = _date_diff(_dates(r, today), _dates(l, today))
            rows.append(
                {
                    "status": "date_mismatch" if diff else "consistent",
                    "detail": diff,
                    "resume": r["evidence"]["quote"],
                    "linkedin": l["evidence"]["quote"],
                }
            )
        else:
            rows.append({"status": "only_resume", "detail": None, "resume": r["evidence"]["quote"], "linkedin": None})
    for i, l in enumerate(linkedin_roles):
        if i not in used:
            rows.append({"status": "only_linkedin", "detail": None, "resume": None, "linkedin": l["evidence"]["quote"]})
    order = {"date_mismatch": 0, "only_resume": 1, "only_linkedin": 2, "consistent": 3}
    rows.sort(key=lambda r: order[r["status"]])
    return rows


def linkedin_check(
    linkedin_text: str,
    resume_text: str,
    resume_profile: dict,
    resume_source: str,
    provider: AIProvider | None,
    fallback_reason: str | None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    text = clean_jd_text(linkedin_text)  # same normalisation and limits as pasted text elsewhere
    li = extract_profile(text, provider, fallback_reason)

    resume_skills = group_by_skill(find_mentions(resume_text))
    li_skills = group_by_skill(find_mentions(text))
    skills = {
        "both": sorted(set(resume_skills) & set(li_skills)),
        "only_resume": sorted(set(resume_skills) - set(li_skills)),
        "only_linkedin": [
            {"skill": s, "quote": li_skills[s][0].quote} for s in sorted(set(li_skills) - set(resume_skills))
        ],
    }
    roles = compare_roles(resume_profile.get("experience", []), li["experience"], today)
    notices = list(li["notices"])
    if resume_source != li["source"]:
        notices.append(
            "The resume and LinkedIn text were read with different methods (AI vs pattern-based), "
            "so role matching may be less reliable. Re-run the analysis to align them."
        )
    if not li["experience"]:
        notices.append(
            "No dated roles were found in the pasted text. Paste your LinkedIn Experience section, including the dates."
        )
    return {
        "source": li["source"],
        "model": li["model"],
        "fallback_reason": li["fallback_reason"],
        "linkedin_text": text,
        "roles": roles,
        "skills": skills,
        "notices": notices,
        "label": "Consistency check between two documents you provided. It does not verify either one.",
    }
