"""Health check and sample documents."""

from typing import Literal

from pydantic import BaseModel, Field


class SampleDocument(BaseModel):
    filename: str
    text: str


class SamplesResponse(BaseModel):
    resume: SampleDocument
    job_description: SampleDocument


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
    ai_model: str | None = Field(description="Gemini model used when AI is live, else null.")
    semantic_matching: Literal["enabled", "disabled"] = Field(description="Whether SEMANTIC_MATCHING is on.")
    ai_timeout_seconds: float = Field(description="Most seconds one AI request may take (AI_TIMEOUT_SECONDS).")
