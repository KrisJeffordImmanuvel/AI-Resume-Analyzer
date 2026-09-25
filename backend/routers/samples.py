"""Sample documents for "Try with sample data", so a first-time user can see a report straight away."""

from fastapi import APIRouter, HTTPException

from config import BACKEND_DIR
from schemas import SampleDocument, SamplesResponse

router = APIRouter(prefix="/api/samples", tags=["samples"])

SAMPLES_DIR = BACKEND_DIR.parent / "samples"
RESUME = "sample_resume.txt"
JOB_DESCRIPTION = "sample_job_description.txt"


def _read(name: str) -> SampleDocument:
    return SampleDocument(filename=name, text=(SAMPLES_DIR / name).read_text(encoding="utf-8"))


@router.get("", response_model=SamplesResponse)
def get_samples() -> SamplesResponse:
    """The fictional sample resume and job description from the samples folder."""
    try:
        return SamplesResponse(resume=_read(RESUME), job_description=_read(JOB_DESCRIPTION))
    except OSError:
        raise HTTPException(404, "The sample files are missing from the samples folder.")
