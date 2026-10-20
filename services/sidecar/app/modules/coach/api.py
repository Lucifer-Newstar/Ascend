from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.coach import service, weekly_review

router = APIRouter(prefix="/coach", tags=["coach"])


class AskIn(BaseModel):
    question: str = Field(default="", max_length=1000)


class CoachOut(BaseModel):
    source: str
    text: str
    tip_code: str
    model: str | None
    fallback_reason: str | None


class CoachStatus(BaseModel):
    ai_enabled: bool
    ollama_available: bool
    model: str


@router.get("/status", response_model=CoachStatus)
def coach_status(request: Request, db: Session = Depends(get_db)) -> CoachStatus:
    return CoachStatus(**service.status(db, request.app.state.settings))  # type: ignore[arg-type]


@router.get("/tip", response_model=CoachOut)
def tip(
    request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> CoachOut:
    r = service.reply(db, request.app.state.settings, now, None)
    return CoachOut(**r.__dict__)


@router.post("/ask", response_model=CoachOut)
def ask(
    body: AskIn, request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> CoachOut:
    r = service.reply(db, request.app.state.settings, now, body.question or None)
    return CoachOut(**r.__dict__)


class FindingOut(BaseModel):
    code: str
    severity: int
    title: str
    detail: str
    proposal: str | None
    numbers: dict[str, object]


class WeeklyReviewOut(BaseModel):
    week_start: date
    week_end: date
    sessions_done: int
    sessions_planned: int
    findings: list[FindingOut]
    top: list[FindingOut]
    summary: str
    summary_source: str
    algo_version: str


@router.get("/weekly-review/latest", response_model=WeeklyReviewOut)
def latest_weekly_review(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> WeeklyReviewOut:
    """Review of the last 7 days: every finding from the fixed rules, the top 3 by
    severity, and a template summary that only repeats the findings' numbers."""
    r = weekly_review.review(db, now)

    def out(f: weekly_review.Finding) -> FindingOut:
        return FindingOut(
            code=f.code,
            severity=f.severity,
            title=f.title,
            detail=f.detail,
            proposal=f.proposal,
            numbers=f.numbers,
        )

    return WeeklyReviewOut(
        week_start=r.week_start,
        week_end=r.week_end,
        sessions_done=r.sessions_done,
        sessions_planned=r.sessions_planned,
        findings=[out(f) for f in r.findings],
        top=[out(f) for f in r.top],
        summary=r.summary,
        summary_source=r.summary_source,
        algo_version=r.algo_version,
    )
