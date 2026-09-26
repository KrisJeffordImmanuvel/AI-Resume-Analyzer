"""Job Provider mode."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.analysis import Priority


class JobSummary(BaseModel):
    id: int
    created_at: datetime
    title: str
    jd_source: Literal["upload", "paste"]
    jd_filename: str | None
    candidate_count: int


class JobSkill(BaseModel):
    skill: str
    priority: Priority
    jd_quote: str


class MatrixCell(BaseModel):
    status: Literal["named", "related", "missing"]
    match_type: Literal["exact", "literal", "ai_inferred", "semantic"] | None
    quote: str | None = Field(description="Verbatim resume text supporting the skill, if any.")


class CandidateRow(BaseModel):
    rank: int
    analysis_id: int
    filename: str
    added_at: datetime
    score: int | None
    required_matched: int
    required_related: int
    required_total: int
    missing_required: list[str]
    extraction: Literal["ai", "fallback"]
    cells: dict[str, MatrixCell] = Field(description="Keyed by skill name, one entry per job skill.")


class JobDetail(JobSummary):
    jd_text: str
    skills: list[JobSkill]
    candidates: list[CandidateRow]
    label: str


class UploadOutcome(BaseModel):
    filename: str
    status: Literal["added", "duplicate", "error"]
    analysis_id: int | None = None
    message: str | None = None


class CandidateUploadResponse(BaseModel):
    outcomes: list[UploadOutcome]
    job: JobDetail
