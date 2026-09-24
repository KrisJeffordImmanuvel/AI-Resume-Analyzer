"""Pydantic response models. These also drive the examples on the /docs page."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(description="Always 'ok' when the API is up.")
    version: str = Field(description="Backend application version.", examples=["0.1.0"])
    ai_configured: bool = Field(description="True when GOOGLE_API_KEY is set.")
    demo_mode: bool = Field(description="True when DEMO_MODE is enabled.")
    ai_mode: Literal["live", "fallback"] = Field(
        description="'live' when AI is used; 'fallback' when deterministic fallbacks are used."
    )
    fallback_reason: Literal["no_api_key", "demo_mode"] | None = Field(
        description="Why AI is in fallback mode, or null when AI is live."
    )
    database: Literal["ok", "error"] = Field(description="Whether the database answered a test query.")
