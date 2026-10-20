from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.coach import service

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
def tip(request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> CoachOut:
    r = service.reply(db, request.app.state.settings, now, None)
    return CoachOut(**r.__dict__)


@router.post("/ask", response_model=CoachOut)
def ask(body: AskIn, request: Request, db: Session = Depends(get_db),
        now: datetime = Depends(get_now)) -> CoachOut:
    r = service.reply(db, request.app.state.settings, now, body.question or None)
    return CoachOut(**r.__dict__)
