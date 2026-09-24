"""Local semantic matching with Sentence Transformers.

Used only for JD skills that the literal engine could not find. The resume is
split into short verbatim units (lines, or sentences of long lines); the unit
most similar to the missing skill is offered as related evidence if its cosine
similarity clears the threshold. Tests use a fake Embedder, never the real model.
"""

import math
import re
import threading
from typing import Protocol

from skills import MAX_QUOTE_CHARS, _URL_OR_EMAIL


class EmbedderUnavailable(Exception):
    """The embedding model could not be loaded or run. Message is user-safe."""


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Loads the model on first use (the first analysis may take a while)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._error: str | None = None

    def _load(self):
        with self._lock:
            if self._model is not None:
                return self._model
            if self._error:
                raise EmbedderUnavailable(self._error)
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                self._error = "sentence-transformers is not installed (run: pip install -r requirements.txt)."
                raise EmbedderUnavailable(self._error)
            try:
                self._model = SentenceTransformer(self.model_name, device="cpu")
            except Exception as exc:  # usually the first-time download failing
                raise EmbedderUnavailable(
                    f"Could not load the semantic model '{self.model_name}' ({type(exc).__name__}). "
                    "The first run needs internet access to download it."
                ) from exc
            return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vectors]


_embedders: dict[str, SentenceTransformerEmbedder] = {}
_embedders_lock = threading.Lock()


def shared_embedder(model_name: str) -> SentenceTransformerEmbedder:
    """One embedder per model name for the whole process, so the model loads once."""
    with _embedders_lock:
        if model_name not in _embedders:
            _embedders[model_name] = SentenceTransformerEmbedder(model_name)
        return _embedders[model_name]


# ---- Matching ------------------------------------------------------------------

_SENTENCE_BREAK = re.compile(r"(?<=[.;!?])\s+")
_MIN_UNIT_WORDS = 3
_WORD = re.compile(r"[A-Za-z]{2,}")


def resume_units(text: str) -> list[str]:
    """Verbatim, reasonably short pieces of the resume to compare against."""
    masked = _URL_OR_EMAIL.sub(" ", text)
    units = []
    for line in masked.split("\n"):
        line = line.strip()
        pieces = [line] if len(line) <= MAX_QUOTE_CHARS else _SENTENCE_BREAK.split(line)
        for piece in pieces:
            piece = piece.strip()[:MAX_QUOTE_CHARS]
            if len(_WORD.findall(piece)) >= _MIN_UNIT_WORDS and piece in text and piece not in units:
                units.append(piece)
    return units


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def best_matches(
    skill_names: list[str], resume_text: str, embedder: Embedder, threshold: float
) -> dict[str, tuple[str, float]]:
    """For each skill, the most similar resume unit and its similarity, if >= threshold."""
    units = resume_units(resume_text)
    if not skill_names or not units:
        return {}
    queries = [f"Experience with {name}" for name in skill_names]
    vectors = embedder.encode(queries + units)
    query_vecs, unit_vecs = vectors[: len(queries)], vectors[len(queries):]
    out = {}
    for name, qv in zip(skill_names, query_vecs):
        scored = [(_cosine(qv, uv), unit) for uv, unit in zip(unit_vecs, units)]
        similarity, unit = max(scored)
        if similarity >= threshold:
            out[name] = (unit, round(similarity, 3))
    return out
