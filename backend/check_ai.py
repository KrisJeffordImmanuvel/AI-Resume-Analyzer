"""Manual check that AI and semantic matching work on this machine.

Run from the backend folder (with the venv active):
    python check_ai.py

This makes one small real Gemini request (if a key is set) and loads the local
semantic model (downloading it the first time). It is NOT part of pytest.
"""

import sys
import time
from pathlib import Path

from pydantic import BaseModel

from ai_provider import AIError, make_provider
from config import get_settings
from parsing import normalize_text
from semantic import EmbedderUnavailable, SentenceTransformerEmbedder, _cosine, best_matches, skill_query
from skills import find_mentions, group_by_skill

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


class _Ping(BaseModel):
    ok: bool
    reply: str


def check_gemini(settings) -> bool:
    print("== Gemini ==")
    print(f"  API key set : {'yes' if settings.has_api_key else 'no'}")
    print(f"  DEMO_MODE   : {settings.demo_mode}")
    print(f"  Model       : {settings.gemini_model}")
    provider = make_provider(settings)
    if provider is None:
        print("  SKIPPED: AI is off (no key, or DEMO_MODE=true). The app will use fallbacks.")
        return True
    start = time.perf_counter()
    try:
        out = provider.generate_json(
            system="Reply in JSON.",
            prompt='Return {"ok": true, "reply": "pong"}.',
            schema=_Ping,
        )
    except AIError as exc:
        print(f"  FAILED: {exc}")
        print("  Check the key at https://aistudio.google.com/apikey, or set GEMINI_MODEL to a model your key can use.")
        return False
    print(f"  OK in {time.perf_counter() - start:.1f}s: {out}")
    return True


def check_semantic(settings) -> bool:
    print("== Semantic matching ==")
    print(f"  Enabled   : {settings.semantic_matching}")
    print(f"  Model     : {settings.semantic_model}")
    print(f"  Threshold : {settings.semantic_threshold}")
    if not settings.semantic_matching:
        print("  SKIPPED: SEMANTIC_MATCHING=false.")
        return True
    embedder = SentenceTransformerEmbedder(settings.semantic_model)
    query = skill_query("CI/CD")
    lines = [
        "Containerized services with Docker and deployed them to AWS using GitHub Actions.",
        "Mentored two junior engineers and led weekly code reviews.",
    ]
    start = time.perf_counter()
    try:
        vectors = embedder.encode([query] + lines)
    except EmbedderUnavailable as exc:
        print(f"  FAILED: {exc}")
        return False
    print(f"  Model loaded and ran in {time.perf_counter() - start:.1f}s (first run includes the download).")
    for line, vec in zip(lines, vectors[1:]):
        sim = _cosine(vectors[0], vec)
        verdict = "MATCH" if sim >= settings.semantic_threshold else "no match"
        print(f"  {sim:.2f} {verdict:8s} '{query}' vs '{line}'")
    calibrate(embedder, settings.semantic_threshold)
    return True


def calibrate(embedder, threshold: float) -> None:
    """Best resume line for every sample JD skill, to help choose SEMANTIC_THRESHOLD."""
    resume = normalize_text((SAMPLES / "sample_resume.txt").read_text(encoding="utf-8"))
    jd = normalize_text((SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8"))
    named = set(group_by_skill(find_mentions(resume)))
    skills = sorted(group_by_skill(find_mentions(jd)))
    best = best_matches(skills, resume, embedder, threshold=-1.0)
    print("\n== Calibration (sample resume vs sample job description) ==")
    print("  'named' = the resume names this skill (a true match); 'not named' = it does not.")
    print(f"  Current threshold: {threshold}\n")
    rows = sorted(((best[s][1], s, s in named, best[s][0]) for s in skills if s in best), reverse=True)
    for sim, skill, is_named, line in rows:
        tag = "named    " if is_named else "not named"
        print(f"  {sim:.2f}  {tag}  {skill:<14} <- {line[:70]}")


if __name__ == "__main__":
    settings = get_settings()
    results = [check_gemini(settings), check_semantic(settings)]
    print("\nAll checks passed." if all(results) else "\nSome checks failed (see above).")
    sys.exit(0 if all(results) else 1)
