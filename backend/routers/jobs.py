"""Job Provider mode: set a job description once, compare many candidates against it."""

from datetime import timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_provider import AIProvider
from comparison import compare
from config import Settings, get_settings
from models import Job, JobCandidate
from parsing import ParseError, clean_jd_text, extract_jd_file_text, extract_resume_text
from routers.analyses import _read_limited, _upgrade_legacy, analyze_and_save, get_ai_provider, get_db, get_embedder
from schemas import CandidateUploadResponse, JobDetail, JobSummary
from semantic import Embedder

router = APIRouter(prefix="/api/jobs", tags=["job provider"])

MAX_FILES_PER_UPLOAD = 10
MAX_TITLE = 200


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _summary(job: Job) -> dict:
    return {
        "id": job.id, "created_at": _utc(job.created_at), "title": job.title, "jd_source": job.jd_source,
        "jd_filename": job.jd_filename, "candidate_count": len(job.candidates),
    }


def _detail(job: Job) -> JobDetail:
    candidates = [
        {"analysis_id": c.analysis_id, "filename": c.analysis.resume_filename, "created_at": _utc(c.created_at),
         "result": _upgrade_legacy(c.analysis.result)}
        for c in job.candidates
    ]
    return JobDetail(**_summary(job), jd_text=job.jd_text, **compare(job.jd_text, candidates))


def _load_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


def _default_title(jd_text: str) -> str:
    first = next((line.strip() for line in jd_text.split("\n") if line.strip()), "Untitled job")
    return first[:MAX_TITLE]


@router.post("", response_model=JobDetail, status_code=201)
async def create_job(
    title: str | None = Form(None, max_length=MAX_TITLE, description="Defaults to the JD's first line."),
    jd_file: UploadFile | None = File(None, description="Job description as a .txt file."),
    jd_text: str | None = Form(None, description="Job description as pasted text."),
    db: Session = Depends(get_db),
) -> JobDetail:
    has_file = jd_file is not None and bool(jd_file.filename)
    has_text = bool(jd_text and jd_text.strip())
    if has_file == has_text:
        raise HTTPException(422, "Provide the job description either as a .txt file or as pasted text (exactly one).")
    try:
        text = (extract_jd_file_text(jd_file.filename, await _read_limited(jd_file)) if has_file
                else clean_jd_text(jd_text))
    except ParseError as exc:
        raise HTTPException(exc.status, exc.message) from exc
    job = Job(
        title=(title or "").strip()[:MAX_TITLE] or _default_title(text),
        jd_source="upload" if has_file else "paste",
        jd_filename=jd_file.filename if has_file else None,
        jd_text=text,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _detail(job)


@router.get("", response_model=list[JobSummary])
def list_jobs(db: Session = Depends(get_db)) -> list[JobSummary]:
    jobs = db.scalars(select(Job).order_by(Job.id.desc())).all()
    return [JobSummary(**_summary(j)) for j in jobs]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetail:
    return _detail(_load_job(db, job_id))


@router.post("/{job_id}/candidates", response_model=CandidateUploadResponse, status_code=201)
async def add_candidates(
    job_id: int,
    resumes: list[UploadFile] = File(..., description=f"Up to {MAX_FILES_PER_UPLOAD} resumes (PDF, DOCX or TXT)."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
    embedder: Embedder | None = Depends(get_embedder),
) -> CandidateUploadResponse:
    job = _load_job(db, job_id)
    if len(resumes) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(422, f"Upload at most {MAX_FILES_PER_UPLOAD} resumes at a time.")
    existing_texts = {c.analysis.resume_text for c in job.candidates}
    outcomes = []
    for upload in resumes:
        name = upload.filename or "resume"
        try:
            text = extract_resume_text(name, await _read_limited(upload))
        except ParseError as exc:
            outcomes.append({"filename": name, "status": "error", "message": exc.message})
            continue
        if text in existing_texts:
            outcomes.append({"filename": name, "status": "duplicate",
                             "message": "This resume is already in the comparison."})
            continue
        # Exactly the same path as Job Seeker mode.
        analysis = await analyze_and_save(
            db, settings, provider, embedder,
            resume_filename=name, resume_text=text, jd_text=job.jd_text,
            jd_source=job.jd_source, jd_filename=job.jd_filename,
        )
        db.add(JobCandidate(job_id=job.id, analysis_id=analysis.id))
        db.commit()
        existing_texts.add(text)
        outcomes.append({"filename": name, "status": "added", "analysis_id": analysis.id})
    db.refresh(job)
    return CandidateUploadResponse(outcomes=outcomes, job=_detail(job))


@router.delete("/{job_id}/candidates/{analysis_id}", status_code=204)
def remove_candidate(job_id: int, analysis_id: int, db: Session = Depends(get_db)) -> Response:
    job = _load_job(db, job_id)
    link = next((c for c in job.candidates if c.analysis_id == analysis_id), None)
    if link is None:
        raise HTTPException(404, "Candidate not found in this job.")
    job.candidates.remove(link)  # the analysis itself is kept
    db.commit()
    return Response(status_code=204)
