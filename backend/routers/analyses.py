"""Job Seeker analysis endpoints: upload a resume + JD, get an evidence-backed fit report."""

from datetime import timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from matching import analyze
from models import Analysis
from parsing import MAX_UPLOAD_BYTES, ParseError, clean_jd_text, extract_jd_file_text, extract_resume_text
from schemas import AnalysisResponse

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def get_db(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


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
        **row.result,
    )


@router.post("", response_model=AnalysisResponse, status_code=201)
async def create_analysis(
    resume: UploadFile = File(..., description="Resume as PDF, DOCX or TXT."),
    jd_file: UploadFile | None = File(None, description="Job description as a .txt file."),
    jd_text: str | None = Form(None, description="Job description as pasted text."),
    db: Session = Depends(get_db),
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

    result = analyze(resume_text, job_text)
    row = Analysis(
        resume_filename=resume.filename or "resume",
        resume_text=resume_text,
        jd_source="upload" if has_file else "paste",
        jd_filename=jd_file.filename if has_file else None,
        jd_text=job_text,
        score=result["score"]["value"],
        result=result,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisResponse:
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise HTTPException(404, "Analysis not found.")
    return _to_response(row)
