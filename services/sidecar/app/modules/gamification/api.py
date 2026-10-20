from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service, stats
from app.modules.gamification.schemas import GameSummary, QuestItemOut, StatOut, StatsOut

router = APIRouter(prefix="/game", tags=["gamification"])


@router.get("/summary", response_model=GameSummary)
def summary(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> GameSummary:
    return service.summary(db, bus, now)


@router.post("/quests/{item_id}/complete", response_model=QuestItemOut)
def complete(
    item_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> QuestItemOut:
    try:
        return QuestItemOut.model_validate(service.complete_manual(db, bus, item_id, now))
    except service.QuestNotFound as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(409, str(e)) from e


@router.get("/stats", response_model=StatsOut)
def hunter_stats(
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> StatsOut:
    """STR, AGI, END, VIT and INT (0-100), each with its formula and inputs (stats-v1)."""
    rows = stats.compute_stats(stats.gather(db, now))
    return StatsOut(
        stats=[
            StatOut(key=s.key, label=s.label, value=s.value, formula=s.formula, inputs=s.inputs)
            for s in rows
        ],
        version=stats.STATS_VERSION,
        window_days=stats.WINDOW_DAYS,
    )
