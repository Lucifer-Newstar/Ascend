"""Player state and content selector endpoints (select-v1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.selector import catalog, engine, service
from app.modules.selector.state import STATE_VERSION

router = APIRouter(prefix="/selector", tags=["selector"])


class PlayerStateOut(BaseModel):
    level: str
    game_level: int
    age: int | None
    under_18: bool
    training_weeks: float
    sets_per_week: float
    ratios: dict[str, float | None]
    load: dict[str, float]
    most_under: str | None
    readiness: int
    readiness_source: str
    streak: int
    days_since_workout: int | None
    sessions_14d: int
    planned_per_week: int
    kcal_ratio: float | None
    protein_ratio: float | None
    meal_days_7d: int
    goal: str | None
    weight_trend_kg_week: float | None
    trend_matches_goal: bool | None
    hide_calories: bool
    algo_version: str


class PickOut(BaseModel):
    id: int
    day: date
    source: str
    item_id: str
    kind: str
    text: str
    why: list[str]
    created_at: datetime


class ItemCheckOut(BaseModel):
    id: str
    kind: str
    eligible: bool
    why: list[str]
    blocked_by: str | None


class ExplainOut(BaseModel):
    items: list[ItemCheckOut]
    daily_cap: int
    kind_cap: dict[str, int]
    catalog_version: str
    engine_version: str
    state_version: str


def _pick(p: Any) -> PickOut:
    return PickOut(
        id=p.id, day=p.day, source=p.source, item_id=p.item_id, kind=p.kind, text=p.text,
        why=p.why, created_at=p.created_at,
    )  # fmt: skip


@router.get("/state", response_model=PlayerStateOut)
def get_state(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> PlayerStateOut:
    """The player state the selector reads (player-state-v1)."""
    d = service.player_state(db, now).as_dict()
    d["ratios"] = dict(d["ratios"])  # type: ignore[call-overload]
    return PlayerStateOut.model_validate(d)


@router.get("/today", response_model=list[PickOut])
def get_today(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> list[PickOut]:
    """Today's catalog picks with their why (selected once a day)."""
    return [_pick(p) for p in service.today(db, now)]


@router.get("/log", response_model=list[PickOut])
def get_log(db: Session = Depends(get_db)) -> list[PickOut]:
    """The last 20 proactive posts of every source (catalog, watcher, System) with why."""
    return [_pick(p) for p in service.latest(db)]


@router.get("/explain", response_model=ExplainOut)
def get_explain(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> ExplainOut:
    """Every catalog item: eligible right now or not, and the rule that decided it."""
    return ExplainOut(
        items=[ItemCheckOut.model_validate(i) for i in service.explain(db, now)],
        daily_cap=engine.DAILY_CAP,
        kind_cap=engine.KIND_CAP,
        catalog_version=catalog.CATALOG_VERSION,
        engine_version=engine.ENGINE_VERSION,
        state_version=STATE_VERSION,
    )
