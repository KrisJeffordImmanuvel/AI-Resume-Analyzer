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


# ---- Phase 3: roadmap and mock interview ------------------------------------

FallbackReason = Literal["no_api_key", "demo_mode", "provider_error"]


class RoadmapItem(BaseModel):
    skill: str
    category: str
    priority: Priority
    kind: Literal["learn", "strengthen"] = Field(
        description="'learn': missing from the resume. 'strengthen': only related (half-credit) evidence."
    )
    jd_evidence: list[Evidence]
    resume_evidence: list[Evidence]
    steps: list[str]
    project_idea: str | None
    steps_source: Literal["ai", "template"]
    youtube_url: str = Field(description="YouTube search link built from the skill name (never from AI).")


class RoadmapResponse(BaseModel):
    analysis_id: int
    created_at: datetime
    source: Literal["ai", "fallback"]
    model: str | None
    fallback_reason: FallbackReason | None
    notices: list[str]
    items: list[RoadmapItem]


class Grounding(BaseModel):
    source: Literal["resume", "jd"]
    quote: str = Field(description="Verbatim text the question is based on.")


class InterviewQuestionOut(BaseModel):
    id: int
    type: Literal["skill", "gap", "experience", "behavioral"]
    skill: str | None
    question: str
    grounding: Grounding | None


class InterviewSetResponse(BaseModel):
    id: int
    analysis_id: int
    created_at: datetime
    source: Literal["ai", "fallback"]
    model: str | None
    fallback_reason: FallbackReason | None
    notices: list[str]
    questions: list[InterviewQuestionOut]


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)


class FeedbackPoint(BaseModel):
    point: str
    answer_quote: str | None = Field(description="Verbatim words from the answer, if quoted.")


class FeedbackResponse(BaseModel):
    id: int
    question_id: int
    created_at: datetime
    answer: str
    source: Literal["ai", "fallback"]
    model: str | None
    fallback_reason: FallbackReason | None
    notices: list[str]
    rating: int | None = Field(description="AI estimate 1-5; null for rule-based feedback.")
    summary: str
    strengths: list[FeedbackPoint]
    improvements: list[FeedbackPoint]
    follow_up_question: str


# ---- Phase 4: resume quality, rewrites, ATS view ----------------------------

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


# ---- Phase 5: career intelligence -------------------------------------------

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


# ---- Phase 6: external evidence ---------------------------------------------

class GitHubRequest(BaseModel):
    username: str | None = Field(None, max_length=60, description="Omit to use the GitHub link in the resume.")


class RepoRef(BaseModel):
    name: str | None
    url: str | None
    pushed_at: str | None
    via: str | None = None


class GitHubLanguage(BaseModel):
    language: str
    repos: int
    skill: str | None
    examples: list[RepoRef]


class GitHubClaim(BaseModel):
    skill: str
    status: Literal["seen", "not_seen"]
    repos: int
    examples: list[RepoRef]


class GitHubResponse(BaseModel):
    id: int
    created_at: datetime
    username: str
    profile_url: str
    name: str | None
    public_repos: int | None
    followers: int | None
    account_created_at: str | None
    repos_analyzed: int
    recently_active_repos: int
    languages: list[GitHubLanguage]
    resume_claims: list[GitHubClaim]
    not_on_resume: list[GitHubLanguage]
    label: str


class LinkedInRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class RoleComparison(BaseModel):
    status: Literal["consistent", "date_mismatch", "only_resume", "only_linkedin"]
    detail: str | None
    resume: str | None = Field(description="Verbatim resume text for this role.")
    linkedin: str | None = Field(description="Verbatim pasted LinkedIn text for this role.")


class OnlyLinkedInSkill(BaseModel):
    skill: str
    quote: str


class SkillComparison(BaseModel):
    both: list[str]
    only_resume: list[str]
    only_linkedin: list[OnlyLinkedInSkill]


class LinkedInResponse(BaseModel):
    id: int
    created_at: datetime
    source: Literal["ai", "fallback"]
    model: str | None
    fallback_reason: FallbackReason | None
    roles: list[RoleComparison]
    skills: SkillComparison
    notices: list[str]
    label: str


class FairnessFinding(BaseModel):
    category: str
    terms: list[str]
    quote: str = Field(description="The exact line the terms appear in.")
    suggestion: str


class FairnessResponse(BaseModel):
    method: Literal["rule_based"]
    label: str
    job_description: list[FairnessFinding]
    resume: list[FairnessFinding]
    scoring_note: str


class EvidenceSummary(BaseModel):
    detected_github_username: str | None
    github: GitHubResponse | None
    linkedin: LinkedInResponse | None


# ---- Phase 7: Job Provider mode ----------------------------------------------

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
