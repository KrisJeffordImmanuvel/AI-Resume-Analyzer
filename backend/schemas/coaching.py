"""Learning roadmap, mock interview questions and answer feedback."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from schemas.analysis import Evidence, Priority

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
