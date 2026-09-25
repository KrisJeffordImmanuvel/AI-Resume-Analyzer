"""Job Seeker analysis endpoints: upload a resume + JD, get an evidence-backed fit report."""

from datetime import timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ai_provider import AIProvider, make_provider
from analysis_service import run_analysis
from config import Settings, get_settings
from models import (
    Analysis, BulletRewrite, ExternalCheck, InterviewAnswer, InterviewQuestion, InterviewSet, JobCandidate, Roadmap,
)
from parsing import MAX_UPLOAD_BYTES, ParseError, clean_jd_text, extract_jd_file_text, extract_resume_text
from schemas import AnalysisResponse, AnalysisSummary
from semantic import Embedder, shared_embedder

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def get_db(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_ai_provider(settings: Settings = Depends(get_settings)) -> AIProvider | None:
    """None when AI is disabled. Tests override this with a fake provider."""
    return make_provider(settings)


def get_embedder(settings: Settings = Depends(get_settings)) -> Embedder | None:
    """None when semantic matching is disabled. Tests override this with a fake."""
    return shared_embedder(settings.semantic_model) if settings.semantic_matching else None


_OLD_AI_OFF_NOTICE = "AI extraction is off because"


def _upgrade_legacy(result: dict) -> dict:
    """Older saved results in the current response shape."""
    if "sources" in result:
        notices = result["sources"].get("notices", [])
        if any(n.startswith(_OLD_AI_OFF_NOTICE) for n in notices):
            # Saved before AI being off stopped counting as a notice.
            result = {**result, "sources": {**result["sources"],
                                            "notices": [n for n in notices if not n.startswith(_OLD_AI_OFF_NOTICE)]}}
        return result
    result = dict(result)
    result.pop("method", None)
    result["sources"] = {
        "extraction": "fallback", "model": None, "fallback_reason": None,
        "semantic": "disabled", "semantic_threshold": None,
        "notices": ["This analysis was saved by an earlier version (keyword matching only)."],
    }
    result["profile"] = {"skills": [], "experience": [], "education": [], "discarded": 0}
    for item in result.get("matched", []):
        item.setdefault("credit", 1.0)
    return result


async def _read_limited(upload: UploadFile) -> bytes:
    # Read one byte past the limit so oversized files are detected without
    # loading arbitrarily large uploads into memory.
    return await upload.read(MAX_UPLOAD_BYTES + 1)


def _to_response(row: Analysis) -> AnalysisResponse:
    created_at = row.created_at
    if created_at.tzinfo is None:  # SQLite drops the timezone; values are stored in UTC.
        created_at = created_at.replace(tzinfo=timezone.utc)
    return AnalysisResponse(
        id=row.id,
        created_at=created_at,
        resume_filename=row.resume_filename,
        jd_source=row.jd_source,
        jd_filename=row.jd_filename,
        **_upgrade_legacy(row.result),
    )


async def analyze_and_save(
    db: Session,
    settings: Settings,
    provider: AIProvider | None,
    embedder: Embedder | None,
    *,
    resume_filename: str,
    resume_text: str,
    jd_text: str,
    jd_source: str,
    jd_filename: str | None,
) -> Analysis:
    """The one analysis path, shared by Job Seeker and Job Provider modes."""
    # AI calls and model loading are slow and blocking, so keep them off the event loop.
    result = await run_in_threadpool(
        run_analysis,
        resume_text,
        jd_text,
        provider=provider,
        fallback_reason=settings.fallback_reason,
        embedder=embedder,
        semantic_threshold=settings.semantic_threshold,
    )
    row = Analysis(
        resume_filename=resume_filename,
        resume_text=resume_text,
        jd_source=jd_source,
        jd_filename=jd_filename,
        jd_text=jd_text,
        score=result["score"]["value"],
        result=result,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("", response_model=AnalysisResponse, status_code=201)
async def create_analysis(
    resume: UploadFile = File(..., description="Resume as PDF, DOCX or TXT."),
    jd_file: UploadFile | None = File(None, description="Job description as a .txt file."),
    jd_text: str | None = Form(None, description="Job description as pasted text."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
    embedder: Embedder | None = Depends(get_embedder),
) -> AnalysisResponse:
    has_file = jd_file is not None and bool(jd_file.filename)
    has_text = bool(jd_text and jd_text.strip())
    if has_file == has_text:
        raise HTTPException(422, "Provide the job description either as a .txt file or as pasted text (exactly one).")

    try:
        resume_text = extract_resume_text(resume.filename or "", await _read_limited(resume))
        if has_file:
            job_text = extract_jd_file_text(jd_file.filename, await _read_limited(jd_file))
        else:
            job_text = clean_jd_text(jd_text)
    except ParseError as exc:
        raise HTTPException(exc.status, exc.message) from exc

    row = await analyze_and_save(
        db, settings, provider, embedder,
        resume_filename=resume.filename or "resume",
        resume_text=resume_text,
        jd_text=job_text,
        jd_source="upload" if has_file else "paste",
        jd_filename=jd_file.filename if has_file else None,
    )
    return _to_response(row)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    return _to_response(row)


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[AnalysisSummary]:
    """Recent Job Seeker analyses, newest first (Job Provider candidates are listed under their job)."""
    in_jobs = select(JobCandidate.analysis_id)
    rows = db.scalars(
        select(Analysis).where(Analysis.id.not_in(in_jobs)).order_by(Analysis.id.desc()).limit(limit)
    ).all()
    out = []
    for row in rows:
        title = next((line.strip() for line in row.jd_text.split("\n") if line.strip()), "")
        created_at = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
        out.append(AnalysisSummary(
            id=row.id, created_at=created_at, resume_filename=row.resume_filename, jd_title=title[:120],
            score=row.score, extraction=_upgrade_legacy(row.result)["sources"]["extraction"],
        ))
    return out


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)) -> Response:
    """Permanently delete an analysis, its resume text and everything generated from it."""
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    set_ids = select(InterviewSet.id).where(InterviewSet.analysis_id == analysis_id)
    question_ids = select(InterviewQuestion.id).where(InterviewQuestion.set_id.in_(set_ids))
    db.execute(delete(InterviewAnswer).where(InterviewAnswer.question_id.in_(question_ids)))
    db.execute(delete(InterviewQuestion).where(InterviewQuestion.set_id.in_(set_ids)))
    for model in (InterviewSet, Roadmap, BulletRewrite, ExternalCheck, JobCandidate):
        db.execute(delete(model).where(model.analysis_id == analysis_id))
    db.delete(row)
    db.commit()
    return Response(status_code=204)
