"""ORM models. Importing this module registers the tables on database.Base."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_text: Mapped[str] = mapped_column(Text)
    jd_source: Mapped[str] = mapped_column(String(10))  # "upload" or "paste"
    jd_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[dict] = mapped_column(JSON)


class Roadmap(Base):
    """Learning roadmap generated for one analysis (latest one is used)."""

    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    data: Mapped[dict] = mapped_column(JSON)


class InterviewSet(Base):
    """A set of mock interview questions generated for one analysis."""

    __tablename__ = "interview_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    sources: Mapped[dict] = mapped_column(JSON)
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview_set", order_by="InterviewQuestion.position"
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(ForeignKey("interview_sets.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSON)  # type, skill, question, grounding
    interview_set: Mapped[InterviewSet] = relationship(back_populates="questions")


class InterviewAnswer(Base):
    """A practice answer and the feedback it received."""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    answer: Mapped[str] = mapped_column(Text)
    feedback: Mapped[dict] = mapped_column(JSON)


class BulletRewrite(Base):
    """One bullet sent to the rewrite workspace and the suggestions it got."""

    __tablename__ = "bullet_rewrites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    data: Mapped[dict] = mapped_column(JSON)


class ExternalCheck(Base):
    """A GitHub or LinkedIn evidence check run for one analysis."""

    __tablename__ = "external_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # "github" or "linkedin"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    data: Mapped[dict] = mapped_column(JSON)


class Job(Base):
    """Job Provider mode: one job description that many candidates are compared against."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    title: Mapped[str] = mapped_column(String(200))
    jd_source: Mapped[str] = mapped_column(String(10))  # "upload" or "paste"
    jd_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_text: Mapped[str] = mapped_column(Text)
    candidates: Mapped[list["JobCandidate"]] = relationship(
        back_populates="job", order_by="JobCandidate.id", cascade="all, delete-orphan"
    )


class JobCandidate(Base):
    """Links a job to one candidate's analysis (a normal Analysis row, same engine)."""

    __tablename__ = "job_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    job: Mapped[Job] = relationship(back_populates="candidates")
    analysis: Mapped[Analysis] = relationship()
