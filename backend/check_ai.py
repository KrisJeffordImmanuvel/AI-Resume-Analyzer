"""Manual check that AI and semantic matching work on this machine.

Run from the backend folder (with the venv active):
    python check_ai.py            # check the configured model and semantic matching
    python check_ai.py --models   # list Gemini models your key can use and ping each

This makes one small real Gemini request (if a key is set) and loads the local
semantic model (downloading it the first time). It is NOT part of pytest.
"""

import sys
import time
from pathlib import Path

from pydantic import BaseModel

from ai_provider import AIError, make_provider, safe_message
from config import get_settings
from parsing import normalize_text
from semantic import EmbedderUnavailable, SentenceTransformerEmbedder, best_matches, cosine, skill_query
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
    print(f"  Fallbacks   : {', '.join(settings.gemini_fallback_models) or 'none'}")
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
    print(f"  OK in {time.perf_counter() - start:.1f}s from {provider.model}: {out}")
    return True


MAX_MODELS_TO_PING = 10


def check_models(settings) -> bool:
    """List Gemini text models this key can use and send each a tiny request."""
    print("== Gemini models for your key ==")
    if not settings.has_api_key:
        print("  No GOOGLE_API_KEY set.")
        return False
    from google import genai
    from google.genai import types

    from ai_provider import GeminiProvider

    print("  Asking Google for the model list (up to 30 seconds)...", flush=True)
    client = genai.Client(api_key=settings.google_api_key, http_options=types.HttpOptions(timeout=30_000))
    try:
        names = [
            m.name.removeprefix("models/")
            for m in client.models.list()
            if "generateContent" in (m.supported_actions or [])
            and m.name.removeprefix("models/").startswith("gemini")
            and not any(x in m.name for x in ("tts", "image", "audio", "live", "embedding"))
        ]
    except Exception as exc:
        print(f"  FAILED to list models: {safe_message(exc, settings.google_api_key)}")
        return False
    # Cheaper "flash" models first; they are the practical choices for this app.
    names.sort(key=lambda n: ("flash" not in n, "preview" in n or "exp" in n, n))
    print(f"  {len(names)} text models available; pinging up to {MAX_MODELS_TO_PING} (one tiny request each).")
    print("  A busy model can take ~10 seconds while it is retried.\n", flush=True)
    working = []
    for name in names[:MAX_MODELS_TO_PING]:
        print(f"  ...     {name}", end="\r", flush=True)
        provider = GeminiProvider(settings.google_api_key, [name], timeout_seconds=30)
        start = time.perf_counter()
        try:
            provider.generate_json(
                system="Reply in JSON.", prompt='Return {"ok": true, "reply": "pong"}.', schema=_Ping
            )
            elapsed = time.perf_counter() - start
            print(f"  OK      {name}  ({elapsed:.1f}s)")
            working.append((elapsed, name))
        except AIError as exc:
            print(f"  FAILED  {name}  {str(exc).split(': ', 1)[-1][:90]}")
    if working:
        # Keep the main model if your key has it (a 503 is temporary); the
        # backups take over while it is busy. Replace it only if it is not offered.
        # Fastest first; skip "-latest" aliases, which may point at the main model
        # and so be busy at the same time.
        ranked = [n for _, n in sorted(working)]
        main = settings.gemini_model if settings.gemini_model in names else ranked[0]
        backups = [n for n in ranked if n != main and not n.endswith("-latest")][:2]
        print("\n  Suggested backend\\.env lines:")
        if main != settings.gemini_model:
            print(f"    GEMINI_MODEL={main}")
        print(
            f"    GEMINI_FALLBACK_MODELS={','.join(backups)}"
            if backups
            else "    (no other working model to use as a backup)"
        )
    return bool(working)


def check_semantic(settings) -> bool:
    print("== Semantic matching ==")
    print(f"  Enabled   : {settings.semantic_matching}")
    print(f"  Model     : {settings.semantic_model}")
    print(f"  Threshold : {settings.semantic_threshold}")
    if not settings.semantic_matching:
        print("  SKIPPED: semantic matching is off (the default). Set SEMANTIC_MATCHING=true to test it.")
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
    for line, vec in zip(lines, vectors[1:], strict=True):
        sim = cosine(vectors[0], vec)
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
    if "--models" in sys.argv:
        sys.exit(0 if check_models(settings) else 1)
    results = [check_gemini(settings), check_semantic(settings)]
    print("\nAll checks passed." if all(results) else "\nSome checks failed (see above).")
    sys.exit(0 if all(results) else 1)
