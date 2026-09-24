"""Pydantic response models. These also drive the examples on the /docs page."""

from datetime import datetime
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


class Evidence(BaseModel):
    quote: str = Field(description="Verbatim line copied from the source text.")
    term: str = Field(description="The exact wording that matched, as it appears in the quote.")
    term_offset: int = Field(description="Character position where `term` starts inside `quote`.")


class MatchedSkill(BaseModel):
    skill: str
    category: str
    priority: Literal["required", "standard", "preferred"]
    match_type: Literal["exact", "literal"] = Field(
        description="'exact': same wording in both documents. 'literal': same skill, different wording (e.g. JS vs JavaScript)."
    )
    resume_evidence: list[Evidence]
    jd_evidence: list[Evidence]


class MissingSkill(BaseModel):
    skill: str
    category: str
    priority: Literal["required", "standard", "preferred"]
    jd_evidence: list[Evidence]


class AdditionalSkill(BaseModel):
    skill: str
    category: str
    resume_evidence: list[Evidence]


class PriorityBreakdown(BaseModel):
    priority: Literal["required", "standard", "preferred"]
    weight: int
    matched: int
    total: int


class Score(BaseModel):
    value: int | None = Field(description="0-100, or null when the JD has no recognizable skills.")
    label: str
    matched_weight: int
    total_weight: int
    breakdown: list[PriorityBreakdown]


class AnalysisResponse(BaseModel):
    id: int
    created_at: datetime
    resume_filename: str
    jd_source: Literal["upload", "paste"]
    jd_filename: str | None
    method: Literal["deterministic"] = Field(description="How the analysis was produced.")
    score: Score
    matched: list[MatchedSkill]
    missing: list[MissingSkill]
    additional: list[AdditionalSkill] = Field(description="Resume skills the JD does not mention.")
    warnings: list[str]
