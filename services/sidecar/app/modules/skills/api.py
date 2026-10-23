from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.skills import custom, service
from app.modules.skills.models import CustomSkill
from app.modules.skills.schemas import (
    CustomSkillIn,
    CustomSkillOut,
    CustomStepOut,
    SkillDetail,
    SkillSummary,
    SkillUnlockOut,
    TrainOut,
)

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


def _custom_out(row: CustomSkill) -> CustomSkillOut:
    return CustomSkillOut(
        id=row.id,
        key=row.key,
        name=row.name,
        family=row.family,
        summary=row.summary,
        steps=[CustomStepOut.model_validate(s) for s in row.steps],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/custom", response_model=list[CustomSkillOut])
def list_custom(db: Session = Depends(get_db)) -> list[CustomSkillOut]:
    """The skill trees you wrote yourself."""
    return [_custom_out(r) for r in custom.rows(db)]


@router.post("/custom", response_model=CustomSkillOut, status_code=201)
def create_custom(
    body: CustomSkillIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> CustomSkillOut:
    """Write your own skill tree: 1 to 8 milestones on library exercises. Evaluated like
    the built-in trees from logged sets; custom milestones pay no XP."""
    try:
        row = custom.create(
            db, body.name, body.family, body.summary, [s.model_dump() for s in body.steps], now
        )
    except custom.CustomSkillError as e:
        raise HTTPException(422, str(e)) from e
    service.evaluate(db, bus, now, {row.key}, source="import")
    return _custom_out(row)


@router.put("/custom/{skill_id}", response_model=CustomSkillOut)
def update_custom(
    skill_id: int,
    body: CustomSkillIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> CustomSkillOut:
    """Change a custom tree. Its milestones are re-judged from your logged sets."""
    try:
        row = custom.update(
            db,
            skill_id,
            body.name,
            body.family,
            body.summary,
            [s.model_dump() for s in body.steps],
            now,
        )
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except custom.CustomSkillError as e:
        raise HTTPException(422, str(e)) from e
    service.evaluate(db, bus, now, {row.key}, source="import")
    return _custom_out(row)


@router.delete("/custom/{skill_id}", status_code=204)
def delete_custom(skill_id: int, db: Session = Depends(get_db)) -> None:
    """Remove a custom tree (your logged sets stay)."""
    try:
        custom.archive(db, skill_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


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
