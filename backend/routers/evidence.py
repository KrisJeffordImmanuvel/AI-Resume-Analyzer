"""External evidence: GitHub (public API), LinkedIn (pasted text), fairness scan."""

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_provider import AIProvider
from config import Settings, get_settings
from fairness import fairness_scan
from github_check import GitHubClient, GitHubError, HttpGitHubClient, detect_username, github_check
from linkedin_check import linkedin_check
from models import ExternalCheck
from parsing import ParseError
from routers.analyses import _upgrade_legacy, get_ai_provider, get_db
from routers.coaching import _load_analysis
from schemas import (
    EvidenceSummary, FairnessResponse, GitHubRequest, GitHubResponse, LinkedInRequest, LinkedInResponse,
)

router = APIRouter(tags=["external evidence"])


def get_github_client(settings: Settings = Depends(get_settings)) -> GitHubClient:
    """Real GitHub client; tests override this with a fake so they never use the network."""
    return HttpGitHubClient(token=settings.github_token)


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _save(db: Session, analysis_id: int, kind: str, data: dict) -> ExternalCheck:
    row = ExternalCheck(analysis_id=analysis_id, kind=kind, data=data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _latest(db: Session, analysis_id: int, kind: str) -> ExternalCheck | None:
    return db.scalars(
        select(ExternalCheck)
        .where(ExternalCheck.analysis_id == analysis_id, ExternalCheck.kind == kind)
        .order_by(ExternalCheck.id.desc())
        .limit(1)
    ).first()


def _response(model, row: ExternalCheck):
    return model(id=row.id, created_at=_utc(row.created_at), **row.data)


@router.get("/api/analyses/{analysis_id}/evidence", response_model=EvidenceSummary)
def get_evidence(analysis_id: int, db: Session = Depends(get_db)) -> EvidenceSummary:
    """Saved checks for this analysis, plus the GitHub username found in the resume."""
    analysis = _load_analysis(db, analysis_id)
    gh, li = _latest(db, analysis_id, "github"), _latest(db, analysis_id, "linkedin")
    return EvidenceSummary(
        detected_github_username=detect_username(analysis.resume_text),
        github=_response(GitHubResponse, gh) if gh else None,
        linkedin=_response(LinkedInResponse, li) if li else None,
    )


@router.post("/api/analyses/{analysis_id}/github", response_model=GitHubResponse, status_code=201)
async def run_github_check(
    analysis_id: int,
    body: GitHubRequest,
    db: Session = Depends(get_db),
    client: GitHubClient = Depends(get_github_client),
) -> GitHubResponse:
    analysis = _load_analysis(db, analysis_id)
    username = (body.username or "").strip() or detect_username(analysis.resume_text)
    if not username:
        raise HTTPException(422, "Enter a GitHub username (no GitHub link was found in the resume).")
    try:
        data = await run_in_threadpool(github_check, username, analysis.resume_text, client)
    except GitHubError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _response(GitHubResponse, _save(db, analysis_id, "github", data))


@router.post("/api/analyses/{analysis_id}/linkedin", response_model=LinkedInResponse, status_code=201)
async def run_linkedin_check(
    analysis_id: int,
    body: LinkedInRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> LinkedInResponse:
    analysis = _load_analysis(db, analysis_id)
    result = _upgrade_legacy(analysis.result)
    try:
        data = await run_in_threadpool(
            linkedin_check, body.text, analysis.resume_text, result.get("profile", {}),
            result["sources"]["extraction"], provider, settings.fallback_reason,
        )
    except ParseError as exc:
        raise HTTPException(exc.status, exc.message.replace("job description", "LinkedIn text")) from exc
    data.pop("linkedin_text", None)  # not needed in the response; the user has it
    return _response(LinkedInResponse, _save(db, analysis_id, "linkedin", data))


@router.get("/api/analyses/{analysis_id}/fairness", response_model=FairnessResponse)
def get_fairness(analysis_id: int, db: Session = Depends(get_db)) -> FairnessResponse:
    analysis = _load_analysis(db, analysis_id)
    return FairnessResponse(**fairness_scan(analysis.resume_text, analysis.jd_text))
