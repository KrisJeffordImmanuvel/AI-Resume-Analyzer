"""Helpers shared by the API routers: FastAPI dependencies and small conversions.

Tests override get_ai_provider and get_embedder (and evidence.get_github_client) with fakes.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ai_provider import AIProvider, make_provider
from config import Settings, get_settings
from models import Analysis
from parsing import MAX_UPLOAD_BYTES
from semantic import Embedder, shared_embedder

# ---- Dependencies ----------------------------------------------------------------


def get_db(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider | None:
    """None when AI is disabled. Tests override this with a fake provider."""
    return make_provider(settings)


def get_embedder(settings: Settings = Depends(get_settings)) -> Embedder | None:
    """None when semantic matching is disabled. Tests override this with a fake."""
    return shared_embedder(settings.semantic_model) if settings.semantic_matching else None


# ---- Helpers ---------------------------------------------------------------------


def utc(value: datetime) -> datetime:
    """SQLite drops the timezone; values are stored in UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def load_analysis(db: Session, analysis_id: int) -> Analysis:
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    return row


async def read_limited(upload: UploadFile) -> bytes:
    """Read one byte past the limit, so oversized files are detected without reading them whole."""
    return await upload.read(MAX_UPLOAD_BYTES + 1)


_OLD_AI_OFF_NOTICE = "AI extraction is off because"


def upgrade_legacy(result: dict) -> dict:
    """Older saved results in the current response shape."""
    if "sources" in result:
        notices = result["sources"].get("notices", [])
        if any(n.startswith(_OLD_AI_OFF_NOTICE) for n in notices):
            # Saved before AI being off stopped counting as a notice.
            result = {
                **result,
                "sources": {
                    **result["sources"],
                    "notices": [n for n in notices if not n.startswith(_OLD_AI_OFF_NOTICE)],
                },
            }
        return result
    # Phase 1 results, saved before AI and semantic matching existed.
    result = dict(result)
    result.pop("method", None)
    result["sources"] = {
        "extraction": "fallback",
        "model": None,
        "fallback_reason": None,
        "semantic": "disabled",
        "semantic_threshold": None,
        "notices": ["This analysis was saved by an earlier version (keyword matching only)."],
    }
    result["profile"] = {"skills": [], "experience": [], "education": [], "discarded": 0}
    for item in result.get("matched", []):
        item.setdefault("credit", 1.0)
    return result
