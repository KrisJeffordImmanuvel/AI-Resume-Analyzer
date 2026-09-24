"""Manual check that AI and semantic matching work on this machine.

Run from the backend folder (with the venv active):
    python check_ai.py

This makes one small real Gemini request (if a key is set) and loads the local
semantic model (downloading it the first time). It is NOT part of pytest.
"""

import sys
import time

from pydantic import BaseModel

from ai_provider import AIError, make_provider
from config import get_settings
from semantic import EmbedderUnavailable, SentenceTransformerEmbedder, _cosine


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
    query = "Experience with CI/CD"
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
    return True


if __name__ == "__main__":
    settings = get_settings()
    results = [check_gemini(settings), check_semantic(settings)]
    print("\nAll checks passed." if all(results) else "\nSome checks failed (see above).")
    sys.exit(0 if all(results) else 1)
