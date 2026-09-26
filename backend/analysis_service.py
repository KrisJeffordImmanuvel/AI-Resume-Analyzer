"""Runs one full analysis: AI (or fallback) profile, literal matching, semantic matching.

The result always says how each part was produced, so the UI can label it.
"""

from ai_provider import AIProvider
from matching import analyze
from profile_extraction import extract_profile
from semantic import Embedder, EmbedderUnavailable, best_matches


def run_analysis(
    resume_text: str,
    jd_text: str,
    *,
    provider: AIProvider | None,
    fallback_reason: str | None,
    embedder: Embedder | None,
    semantic_threshold: float,
) -> dict:
    notices: list[str] = []

    profile = extract_profile(resume_text, provider, fallback_reason)
    notices.extend(profile.pop("notices"))
    ai_skills = {}
    if profile["source"] == "ai":
        for item in profile["skills"]:
            if item["mapped_skill"] and item["mapped_skill"] not in ai_skills:
                ai_skills[item["mapped_skill"]] = item["evidence"]

    semantic_status = "disabled" if embedder is None else "enabled"

    def semantic(names: list[str]) -> dict[str, tuple[str, float]]:
        nonlocal semantic_status
        try:
            return best_matches(names, resume_text, embedder, semantic_threshold)
        except EmbedderUnavailable as exc:
            semantic_status = "unavailable"
            notices.append(f"Semantic matching was skipped: {exc}")
            return {}

    result = analyze(resume_text, jd_text, ai_skills=ai_skills, semantic=semantic if embedder else None)

    # AI being switched off is a normal state shown by `sources`, not a notice. A provider
    # error adds its own notice in extract_profile.
    if profile["discarded"]:
        notices.append(
            f"{profile['discarded']} AI-extracted item(s) were discarded because their quotes "
            "could not be found in the resume."
        )

    result["sources"] = {
        "extraction": profile["source"],
        "model": profile["model"],
        "fallback_reason": profile["fallback_reason"],
        "semantic": semantic_status,
        "semantic_threshold": semantic_threshold if semantic_status == "enabled" else None,
        "notices": notices,
    }
    result["profile"] = {
        "skills": profile["skills"],
        "experience": profile["experience"],
        "education": profile["education"],
        "discarded": profile["discarded"],
    }
    return result
