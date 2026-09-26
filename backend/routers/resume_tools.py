"""Resume intelligence (bullet checks, rewrite workspace) and the ATS / recruiter view."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_provider import AIProvider
from ats import ats_view
from career import career_view
from config import Settings, get_settings
from models import BulletRewrite
from resume_quality import quality_report, rewrite_bullet
from routers.common import get_ai_provider, get_db, load_analysis, upgrade_legacy, utc
from schemas import AtsResponse, CareerResponse, QualityResponse, RewriteRequest, RewriteResponse

router = APIRouter(tags=["resume tools"])


@router.get("/api/analyses/{analysis_id}/quality", response_model=QualityResponse)
def get_quality(analysis_id: int, db: Session = Depends(get_db)) -> QualityResponse:
    return QualityResponse(**quality_report(load_analysis(db, analysis_id).resume_text))


def _rewrite_response(row: BulletRewrite) -> RewriteResponse:
    return RewriteResponse(id=row.id, created_at=utc(row.created_at), **row.data)


@router.post("/api/analyses/{analysis_id}/rewrites", response_model=RewriteResponse, status_code=201)
async def create_rewrite(
    analysis_id: int,
    body: RewriteRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> RewriteResponse:
    analysis = load_analysis(db, analysis_id)
    bullet = body.bullet.strip()
    if not bullet:
        raise HTTPException(422, "Enter a bullet to rewrite.")
    data = await run_in_threadpool(rewrite_bullet, bullet, analysis.resume_text, provider, settings.fallback_reason)
    row = BulletRewrite(analysis_id=analysis_id, data=data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _rewrite_response(row)


@router.get("/api/analyses/{analysis_id}/rewrites", response_model=list[RewriteResponse])
def list_rewrites(analysis_id: int, db: Session = Depends(get_db)) -> list[RewriteResponse]:
    load_analysis(db, analysis_id)
    rows = db.scalars(
        select(BulletRewrite).where(BulletRewrite.analysis_id == analysis_id).order_by(BulletRewrite.id.desc())
    ).all()
    return [_rewrite_response(r) for r in rows]


@router.get("/api/analyses/{analysis_id}/ats", response_model=AtsResponse)
def get_ats(analysis_id: int, db: Session = Depends(get_db)) -> AtsResponse:
    analysis = load_analysis(db, analysis_id)
    profile = upgrade_legacy(analysis.result).get("profile", {})
    return AtsResponse(**ats_view(analysis.resume_text, analysis.jd_text, profile))


@router.get("/api/analyses/{analysis_id}/career", response_model=CareerResponse, response_model_by_alias=True)
def get_career(analysis_id: int, db: Session = Depends(get_db)) -> CareerResponse:
    analysis = load_analysis(db, analysis_id)
    return CareerResponse(**career_view(analysis.resume_text, upgrade_legacy(analysis.result)))
