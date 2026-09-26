"""Your data: delete everything the app has stored, in one step."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from database import Base
from models import Analysis, Job
from routers.common import get_db

router = APIRouter(prefix="/api/data", tags=["your data"])

CONFIRM_WORD = "DELETE"


class DeleteAllRequest(BaseModel):
    confirm: str  # must be "DELETE", so the data is never removed by accident


class DeleteAllResponse(BaseModel):
    analyses_deleted: int
    jobs_deleted: int


@router.post("/delete-all", response_model=DeleteAllResponse)
def delete_all(body: DeleteAllRequest, request: Request, db: Session = Depends(get_db)) -> DeleteAllResponse:
    """Permanently delete every analysis, job, candidate and everything generated from them."""
    if body.confirm != CONFIRM_WORD:
        raise HTTPException(422, f'To delete all data, send {{"confirm": "{CONFIRM_WORD}"}}.')
    analyses = db.scalar(select(func.count()).select_from(Analysis))
    jobs = db.scalar(select(func.count()).select_from(Job))
    for table in reversed(Base.metadata.sorted_tables):  # children before parents
        db.execute(delete(table))
    db.commit()
    engine = request.app.state.engine
    if engine.dialect.name == "sqlite":
        # Rebuild the file so deleted resume text does not linger in its free space.
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM"))
    return DeleteAllResponse(analyses_deleted=analyses, jobs_deleted=jobs)
