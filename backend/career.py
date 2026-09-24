"""Career intelligence: fit across common role profiles, and a dated career timeline.

Role fit uses the same engine as the job-fit score: each role profile is
rendered as a small job description and scored by matching.analyze(), with the
analysis's verified AI skills (if any). The timeline only contains entries whose
dates can be read from resume text; nothing is estimated.
"""

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from matching import analyze
from skills import skill_index

ROLES_PATH = Path(__file__).resolve().parent / "data" / "role_profiles.json"
GAP_MONTHS = 6  # gaps shorter than this are normal job-change time, not flagged

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_POINT = rf"(?:(?P<{{m}}>{_MONTH})\s+)?(?P<{{y}}>(?:19|20)\d\d)"
_RANGE = re.compile(
    _POINT.format(m="m1", y="y1")
    + r"\s*(?:-|–|—|to)\s*(?:"
    + _POINT.format(m="m2", y="y2")
    + r"|(?P<now>present|current|now|today))",
    re.I,
)
_YEAR = re.compile(r"\b(19[5-9]\d|20\d\d)\b")


# ---- Role fit ----------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_roles() -> tuple[dict, ...]:
    return tuple(json.loads(ROLES_PATH.read_text(encoding="utf-8"))["roles"])


def _term(skill_name: str) -> str:
    skill = skill_index()[skill_name]
    return skill.terms[0] if skill.terms else skill.terms_case_sensitive[0]


def role_jd(role: dict) -> str:
    """A role profile written as a job description the engine can read."""
    # No title line: a title like "DevOps / SRE Engineer" would itself be read as skills.
    lines = ["Requirements:"]
    lines += [f"- {_term(s)}" for s in role["required"]]
    lines += ["", "Nice to have:"]
    lines += [f"- {_term(s)}" for s in role["preferred"]]
    return "\n".join(lines)


def role_fits(resume_text: str, ai_skills: dict[str, dict]) -> list[dict]:
    fits = []
    for role in load_roles():
        result = analyze(resume_text, role_jd(role), ai_skills=ai_skills)
        required = result["score"]["breakdown"][0]
        fits.append({
            "id": role["id"],
            "name": role["name"],
            "short": role["short"],
            "score": result["score"]["value"] or 0,
            "required_matched": required["matched"],
            "required_related": required["related"],
            "required_total": required["total"],
            "matched": [m["skill"] for m in result["matched"]],
            "missing_required": [m["skill"] for m in result["missing"] if m["priority"] == "required"],
            "missing_preferred": [m["skill"] for m in result["missing"] if m["priority"] == "preferred"],
        })
    return fits


# ---- Timeline ----------------------------------------------------------------------

def _month(name: str | None) -> int | None:
    return _MONTHS.get(name[:3].lower()) if name else None


def parse_dates(text: str, today: date) -> dict | None:
    """Read a date range ("Jan 2020 - Mar 2022", "2022 - Present") or a single year."""
    m = _RANGE.search(text or "")
    if m:
        start = (int(m["y1"]), _month(m["m1"]) or 1)
        current = bool(m["now"])
        # A bare end year ("2020 - 2022") is read as running to the end of that year.
        end = (today.year, today.month) if current else (int(m["y2"]), _month(m["m2"]) or 12)
        if end < start:
            return None
        return {"start": start, "end": end, "current": current, "text": m.group(0),
                "month_precision": bool(m["m1"])}
    y = _YEAR.search(text or "")
    if y:
        year = int(y.group(1))
        return {"start": (year, 1), "end": (year, 12), "current": False, "text": y.group(0),
                "month_precision": False, "single_year": True}
    return None


def _ym(value: tuple[int, int]) -> str:
    return f"{value[0]:04d}-{value[1]:02d}"


def _months_between(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def build_timeline(profile: dict, today: date | None = None) -> dict:
    today = today or date.today()
    items, undated = [], 0
    for kind, entries, title_key, org_key in (
        ("role", profile.get("experience", []), "title", "organization"),
        ("education", profile.get("education", []), "qualification", "institution"),
    ):
        for e in entries:
            quote = e["evidence"]["quote"]
            parsed = parse_dates(e.get("dates") or "", today) or parse_dates(quote, today)
            if not parsed:
                undated += 1
                continue
            is_point = kind == "education" and parsed.get("single_year")
            items.append({
                "kind": kind,
                "title": e.get(title_key),
                "organization": e.get(org_key),
                "start": _ym(parsed["start"]),
                "end": _ym(parsed["end"]),
                "current": parsed["current"],
                "dates_text": parsed["text"],
                "duration_months": None if is_point else _months_between(parsed["start"], parsed["end"]) + 1,
                "month_precision": parsed["month_precision"],
                "evidence": e["evidence"],
            })
    items.sort(key=lambda i: (i["start"], i["kind"] != "education"))

    roles = [i for i in items if i["kind"] == "role"]
    gaps = []
    for prev, nxt in zip(roles, roles[1:]):
        py, pm = map(int, prev["end"].split("-"))
        ny, nm = map(int, nxt["start"].split("-"))
        gap = _months_between((py, pm), (ny, nm)) - 1
        if gap >= GAP_MONTHS:
            gaps.append({"after": prev["evidence"]["quote"], "before": nxt["evidence"]["quote"],
                         "from": prev["end"], "to": nxt["start"], "months": gap})

    span = None
    if roles:
        first = min(r["start"] for r in roles)
        last = max(r["end"] for r in roles)
        fy, fm = map(int, first.split("-"))
        ly, lm = map(int, last.split("-"))
        span = _months_between((fy, fm), (ly, lm)) + 1

    notices = []
    if undated:
        notices.append(f"{undated} resume entry(ies) had no readable dates, so they are not on the timeline.")
    if any(not r["month_precision"] for r in roles):
        notices.append("Some dates are years only, so durations and gaps are approximate (to the year).")
    return {"items": items, "gaps": gaps, "career_span_months": span, "roles": len(roles), "notices": notices}


def career_view(resume_text: str, result: dict, today: date | None = None) -> dict:
    profile = result.get("profile", {})
    ai_skills = {}
    if result.get("sources", {}).get("extraction") == "ai":
        for s in profile.get("skills", []):
            if s.get("mapped_skill") and s["mapped_skill"] not in ai_skills:
                ai_skills[s["mapped_skill"]] = s["evidence"]
    fits = role_fits(resume_text, ai_skills)
    return {
        "label": "Estimates against generic role profiles, scored with the same engine as the job-fit score. "
                 "Not an official assessment.",
        "profile_source": result.get("sources", {}).get("extraction", "fallback"),
        "roles": fits,
        "timeline": build_timeline(profile, today),
    }
