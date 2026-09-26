"""External evidence: GitHub, LinkedIn, fairness scan."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.coaching import FallbackReason


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
