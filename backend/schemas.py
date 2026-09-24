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
    ai_model: str | None = Field(description="Gemini model used when AI is live, else null.")
    semantic_matching: Literal["enabled", "disabled"] = Field(description="Whether SEMANTIC_MATCHING is on.")


Priority = Literal["required", "standard", "preferred"]


class Evidence(BaseModel):
    quote: str = Field(description="Verbatim text copied from the source document.")
    term: str | None = Field(None, description="The exact wording that matched, if a specific term matched.")
    term_offset: int | None = Field(None, description="Character position where `term` starts inside `quote`.")
    similarity: float | None = Field(None, description="Cosine similarity, for semantic matches only.")


class MatchedSkill(BaseModel):
    skill: str
    category: str
    priority: Priority
    match_type: Literal["exact", "literal", "ai_inferred", "semantic"] = Field(
        description=(
            "'exact': same wording in both documents. 'literal': same skill, different wording "
            "(e.g. JS vs JavaScript). 'ai_inferred': AI judged a verified resume quote to show the skill. "
            "'semantic': the most similar resume line by local embeddings."
        )
    )
    credit: float = Field(description="Share of the skill's weight earned: 1.0 named, 0.5 related evidence.")
    resume_evidence: list[Evidence]
    jd_evidence: list[Evidence]


class MissingSkill(BaseModel):
    skill: str
    category: str
    priority: Priority
    jd_evidence: list[Evidence]


class AdditionalSkill(BaseModel):
    skill: str
    category: str
    resume_evidence: list[Evidence]


class PriorityBreakdown(BaseModel):
    priority: Priority
    weight: int
    matched: int = Field(description="Skills named in the resume (full credit).")
    related: int = Field(0, description="Skills with related evidence only (half credit).")
    total: int


class Score(BaseModel):
    value: int | None = Field(description="0-100, or null when the JD has no recognizable skills.")
    label: str
    matched_weight: float
    total_weight: int
    breakdown: list[PriorityBreakdown]


class Sources(BaseModel):
    extraction: Literal["ai", "fallback"] = Field(description="How the resume profile was produced.")
    model: str | None = Field(None, description="AI provider and model, when AI was used.")
    fallback_reason: Literal["no_api_key", "demo_mode", "provider_error"] | None = None
    semantic: Literal["enabled", "disabled", "unavailable"]
    semantic_threshold: float | None = None
    notices: list[str] = Field(description="Plain-language notes about fallbacks and discarded items.")


class ProfileSkill(BaseModel):
    name: str
    mapped_skill: str | None = Field(description="Matching skill in the curated list, if any.")
    evidence: Evidence


class ExperienceEntry(BaseModel):
    title: str | None
    organization: str | None
    dates: str | None
    evidence: Evidence


class EducationEntry(BaseModel):
    qualification: str | None
    institution: str | None
    dates: str | None
    evidence: Evidence


class Profile(BaseModel):
    skills: list[ProfileSkill]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    discarded: int = Field(description="AI items dropped because their quotes were not in the resume.")


class AnalysisResponse(BaseModel):
    id: int
    created_at: datetime
    resume_filename: str
    jd_source: Literal["upload", "paste"]
    jd_filename: str | None
    sources: Sources
    score: Score
    matched: list[MatchedSkill]
    missing: list[MissingSkill]
    additional: list[AdditionalSkill] = Field(description="Resume skills the JD does not mention.")
    profile: Profile
    warnings: list[str]
