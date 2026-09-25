"""Job Provider comparison: many candidates, one job, one engine.

Every candidate is an ordinary Analysis produced by the same run_analysis() as
Job Seeker mode, so this module only arranges results side by side; it never
scores anything itself.
"""

from matching import analyze

_PRIORITY_RANK = {"required": 0, "standard": 1, "preferred": 2}


def job_skills(jd_text: str) -> list[dict]:
    """The job's skills with priority and JD evidence (the engine run against an empty resume)."""
    missing = analyze("", jd_text)["missing"]
    return sorted(
        ({"skill": m["skill"], "priority": m["priority"], "jd_quote": m["jd_evidence"][0]["quote"]} for m in missing),
        key=lambda s: (_PRIORITY_RANK[s["priority"]], s["skill"].lower()),
    )


def _status(result: dict, skill: str) -> dict:
    for m in result.get("matched", []):
        if m["skill"] == skill:
            full = m.get("credit", 1.0) == 1.0
            return {"status": "named" if full else "related", "match_type": m["match_type"],
                    "quote": m["resume_evidence"][0]["quote"] if m["resume_evidence"] else None}
    return {"status": "missing", "match_type": None, "quote": None}


def compare(jd_text: str, candidates: list[dict]) -> dict:
    """`candidates`: dicts with analysis_id, filename, created_at and result (the stored analysis result)."""
    skills = job_skills(jd_text)
    rows = []
    for c in candidates:
        result = c["result"]
        required = next((b for b in result["score"]["breakdown"] if b["priority"] == "required"),
                        {"matched": 0, "related": 0, "total": 0})
        rows.append({
            "analysis_id": c["analysis_id"],
            "filename": c["filename"],
            "added_at": c["created_at"],
            "score": result["score"]["value"],
            "required_matched": required["matched"],
            "required_related": required.get("related", 0),
            "required_total": required["total"],
            "missing_required": [m["skill"] for m in result["missing"] if m["priority"] == "required"],
            "extraction": result.get("sources", {}).get("extraction", "fallback"),
            "cells": {s["skill"]: _status(result, s["skill"]) for s in skills},
        })
    rows.sort(key=lambda r: (-(r["score"] or 0), -r["required_matched"], r["analysis_id"]))
    for rank, r in enumerate(rows, start=1):
        r["rank"] = rank
    return {
        "skills": skills,
        "candidates": rows,
        "label": "Every candidate is scored by the same engine as Job Seeker mode. Scores are an "
                 "application-generated estimate to support, not replace, human review.",
    }
