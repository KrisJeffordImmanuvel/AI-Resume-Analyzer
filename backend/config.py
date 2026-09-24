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


def get_settings() -> Settings:
    """Read settings fresh from the environment on every call."""
    default_db = f"sqlite:///{(BACKEND_DIR / 'app.db').as_posix()}"
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        demo_mode=os.getenv("DEMO_MODE", "false").strip().lower() in _TRUE_VALUES,
        database_url=os.getenv("DATABASE_URL", "").strip() or default_db,
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
