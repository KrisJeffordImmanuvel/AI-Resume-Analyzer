"""Resume quality, bullet rewrites, ATS view and career intelligence."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.analysis import Evidence
from schemas.coaching import FallbackReason


class BulletIssue(BaseModel):
    code: Literal["no_metric", "weak_opener", "no_action_verb", "too_short", "too_long", "first_person", "filler"]
    severity: Literal["high", "medium", "low"]
    message: str


class BulletCheck(BaseModel):
    text: str = Field(description="The bullet exactly as written in the resume.")
    word_count: int
    quantified: bool
    metric: str | None = Field(description="The first number that reads as a metric (years excluded).")
    verb: Literal["strong", "weak", "unclear"]
    issues: list[BulletIssue]


class QualitySummary(BaseModel):
    bullets: int
    quantified: int
    strong_verb: int
    with_issues: int


class QualityResponse(BaseModel):
    method: Literal["rule_based"]
    summary: QualitySummary
    bullets: list[BulletCheck]
    notices: list[str]


class RewriteRequest(BaseModel):
    bullet: str = Field(min_length=1, max_length=600)


class RewriteVariant(BaseModel):
    text: str
    placeholders: list[str] = Field(description="Bracketed gaps like [X%] for the candidate to fill in.")
    note: str


class RewriteResponse(BaseModel):
    id: int
    created_at: datetime
    bullet: str
    check: BulletCheck
    source: Literal["ai", "fallback"]
    model: str | None
    fallback_reason: FallbackReason | None
    variants: list[RewriteVariant]
    notices: list[str]


class ParseStats(BaseModel):
    words: int
    lines: int
    characters: int


class ContactFound(BaseModel):
    email: bool
    phone: bool
    linkedin: bool
    github: bool


class ParsePreview(BaseModel):
    text: str = Field(description="The resume text exactly as extracted by this app.")
    stats: ParseStats
    headings: list[str]
    contact: ContactFound
    issues: list[str]


class KeywordRow(BaseModel):
    keyword: str = Field(description="Wording used in the job description.")
    kind: Literal["skill", "term"]
    skill: str | None
    jd_count: int
    exact_in_resume: bool = Field(description="The exact wording appears in the resume.")
    skill_in_resume: bool | None = Field(description="For skills: named in the resume in any wording.")


class KeywordSummary(BaseModel):
    total: int
    exact_in_resume: int
    different_wording: int


class KeywordDiff(BaseModel):
    keywords: list[KeywordRow]
    summary: KeywordSummary


class ScanCheck(BaseModel):
    label: str
    passed: bool
    detail: str


class SixSecondScan(BaseModel):
    top_lines: list[str]
    headline: str
    checks: list[ScanCheck]


class AtsResponse(BaseModel):
    label: str
    parse: ParsePreview
    keywords: KeywordDiff
    scan: SixSecondScan


class RoleFit(BaseModel):
    id: str
    name: str
    short: str = Field(description="Short label for chart axes.")
    score: int = Field(description="0-100, same scoring engine as the job-fit score.")
    required_matched: int
    required_related: int
    required_total: int
    matched: list[str]
    missing_required: list[str]
    missing_preferred: list[str]


class TimelineItem(BaseModel):
    kind: Literal["role", "education"]
    title: str | None
    organization: str | None
    start: str = Field(description="YYYY-MM")
    end: str = Field(description="YYYY-MM (the current month when ongoing)")
    current: bool
    dates_text: str = Field(description="The date text as written in the resume.")
    duration_months: int | None
    month_precision: bool
    evidence: Evidence


class TimelineGap(BaseModel):
    after: str
    before: str
    months: int
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class Timeline(BaseModel):
    items: list[TimelineItem]
    gaps: list[TimelineGap]
    career_span_months: int | None
    roles: int
    notices: list[str]


class CareerResponse(BaseModel):
    label: str
    profile_source: Literal["ai", "fallback"]
    roles: list[RoleFit]
    timeline: Timeline
