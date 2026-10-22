from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.skills import service
from app.modules.skills.schemas import SkillDetail, SkillSummary, SkillUnlockOut, TrainOut

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillSummary])
def list_skills(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> list[SkillSummary]:
    """Every calisthenics skill tree with the current step and % to the next."""
    return service.summaries(db, now)


@router.get("/unlocks", response_model=list[SkillUnlockOut])
def recent_unlocks(
    limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)
) -> list[SkillUnlockOut]:
    """Most recent unlocked steps, newest first."""
    return service.recent_unlocks(db, limit)


@router.get("/{skill_key}", response_model=SkillDetail)
def get_skill(
    skill_key: str, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> SkillDetail:
    """One tree: every step with its unlock criteria and progress, feeder exercises, an
    estimated time to the next step (only with enough data) and the sources."""
    try:
        return service.detail(db, skill_key, now)
    except service.SkillNotFound as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{skill_key}/train", response_model=TrainOut)
def train(
    skill_key: str,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> TrainOut:
    """Add today's work for this skill (the next step's exercises and a feeder) to
    today's quest. Idempotent; at most 4 skill items a day."""
    try:
        return service.train(db, bus, skill_key, now)
    except service.SkillNotFound as e:
        raise HTTPException(404, str(e)) from e
