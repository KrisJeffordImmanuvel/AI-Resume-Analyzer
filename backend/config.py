"""Application settings, read from environment variables and backend/.env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent

# Values already present in the environment win over backend/.env.
load_dotenv(BACKEND_DIR / ".env", override=False)

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    google_api_key: str
    demo_mode: bool
    database_url: str
    cors_origins: list[str]
    gemini_model: str
    gemini_fallback_models: list[str]
    ai_timeout_seconds: float
    semantic_matching: bool
    semantic_model: str
    semantic_threshold: float
    github_token: str

    @property
    def has_api_key(self) -> bool:
        return bool(self.google_api_key)

    @property
    def ai_enabled(self) -> bool:
        """AI is used only when a key is set and DEMO_MODE is off."""
        return self.has_api_key and not self.demo_mode

    @property
    def fallback_reason(self) -> str | None:
        if self.demo_mode:
            return "demo_mode"
        if not self.has_api_key:
            return "no_api_key"
        return None


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def get_settings() -> Settings:
    """Read settings fresh from the environment on every call."""
    default_db = f"sqlite:///{(BACKEND_DIR / 'app.db').as_posix()}"
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        demo_mode=os.getenv("DEMO_MODE", "false").strip().lower() in _TRUE_VALUES,
        database_url=os.getenv("DATABASE_URL", "").strip() or default_db,
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or "gemini-3.6-flash",
        gemini_fallback_models=[
            m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()
        ],
        ai_timeout_seconds=_float("AI_TIMEOUT_SECONDS", 60.0),
        # Off by default: calibration showed all-MiniLM-L6-v2 cannot separate related
        # from unrelated resume lines well enough to award credit (see README).
        semantic_matching=os.getenv("SEMANTIC_MATCHING", "false").strip().lower() in _TRUE_VALUES,
        semantic_model=os.getenv("SEMANTIC_MODEL", "").strip() or "sentence-transformers/all-MiniLM-L6-v2",
        semantic_threshold=_float("SEMANTIC_THRESHOLD", 0.6),
        github_token=os.getenv("GITHUB_TOKEN", "").strip(),
    )
