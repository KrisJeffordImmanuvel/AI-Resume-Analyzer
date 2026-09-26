"""Job Seeker coaching: learning roadmap, mock interview questions, answer feedback."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_provider import AIProvider
from config import Settings, get_settings
from interview import build_feedback, build_questions
from models import InterviewAnswer, InterviewQuestion, InterviewSet, Roadmap
from roadmap import build_roadmap
from routers.common import get_ai_provider, get_db, load_analysis, upgrade_legacy, utc
from schemas import AnswerRequest, FeedbackResponse, InterviewSetResponse, RoadmapResponse

router = APIRouter(tags=["coaching"])


def _latest(db: Session, model, analysis_id: int):
    return db.scalars(select(model).where(model.analysis_id == analysis_id).order_by(model.id.desc()).limit(1)).first()


# ---- Roadmap -----------------------------------------------------------------------


def _roadmap_response(row: Roadmap) -> RoadmapResponse:
    return RoadmapResponse(analysis_id=row.analysis_id, created_at=utc(row.created_at), **row.data)


@router.post("/api/analyses/{analysis_id}/roadmap", response_model=RoadmapResponse)
async def create_roadmap(
    analysis_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> RoadmapResponse:
    """Return the saved roadmap for this analysis, or generate one (refresh=true regenerates)."""
    analysis = load_analysis(db, analysis_id)
    existing = _latest(db, Roadmap, analysis_id)
    if existing and not refresh:
        return _roadmap_response(existing)
    data = await run_in_threadpool(build_roadmap, upgrade_legacy(analysis.result), provider, settings.fallback_reason)
    row = Roadmap(analysis_id=analysis_id, data=data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _roadmap_response(row)


# ---- Interview questions ------------------------------------------------------------


def _set_response(row: InterviewSet) -> InterviewSetResponse:
    return InterviewSetResponse(
        id=row.id,
        analysis_id=row.analysis_id,
        created_at=utc(row.created_at),
        **row.sources,
        questions=[{"id": q.id, **q.data} for q in row.questions],
    )


@router.post("/api/analyses/{analysis_id}/interview", response_model=InterviewSetResponse)
async def create_interview(
    analysis_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> InterviewSetResponse:
    """Return the saved question set for this analysis, or generate one (refresh=true regenerates)."""
    analysis = load_analysis(db, analysis_id)
    existing = _latest(db, InterviewSet, analysis_id)
    if existing and not refresh:
        return _set_response(existing)
    questions, sources = await run_in_threadpool(
        build_questions,
        analysis.resume_text,
        analysis.jd_text,
        upgrade_legacy(analysis.result),
        provider,
        settings.fallback_reason,
    )
    row = InterviewSet(analysis_id=analysis_id, sources=sources)
    row.questions = [InterviewQuestion(position=i, data=q) for i, q in enumerate(questions)]
    db.add(row)
    db.commit()
    db.refresh(row)
    return _set_response(row)


# ---- Answer feedback -----------------------------------------------------------------


@router.post("/api/interview/questions/{question_id}/answers", response_model=FeedbackResponse, status_code=201)
async def answer_question(
    question_id: int,
    body: AnswerRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> FeedbackResponse:
    question = db.get(InterviewQuestion, question_id)
    if question is None:
        raise HTTPException(404, "Question not found.")
    answer = body.answer.strip()
    if not answer:
        raise HTTPException(422, "Type an answer before asking for feedback.")
    feedback = await run_in_threadpool(build_feedback, question.data, answer, provider, settings.fallback_reason)
    row = InterviewAnswer(question_id=question_id, answer=answer, feedback=feedback)
    db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackResponse(
        id=row.id, question_id=question_id, created_at=utc(row.created_at), answer=row.answer, **row.feedback
    )
