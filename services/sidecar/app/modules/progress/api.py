from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.gamification.schemas import GameSummary
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.schemas import Totals
from app.modules.progress import energy, history, service
from app.modules.progress.schemas import (
    MuscleStateOut,
    ProfileIn,
    ProfileOut,
    SettingsIn,
    SettingsOut,
)
from app.modules.workouts.models import Workout

router = APIRouter(tags=["progress"])


def _profile_out(db: Session) -> ProfileOut:
    p = service.get_profile(db)
    if p is None:
        raise HTTPException(404, "no profile yet: finish onboarding")
    fields = ("name", "age", "sex", "height_cm", "weight_kg", "goal", "activity")
    data = {k: getattr(p, k) for k in fields}
    return ProfileOut.model_validate({**data, "energy": service.energy_for(p)})


@router.get("/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)) -> ProfileOut:
    return _profile_out(db)


@router.put("/profile", response_model=ProfileOut)
def put_profile(body: ProfileIn, db: Session = Depends(get_db)) -> ProfileOut:
    service.upsert_profile(db, body)
    return _profile_out(db)


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)) -> SettingsOut:
    return SettingsOut(ai_enabled=service.ai_enabled(db))


@router.put("/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, db: Session = Depends(get_db)) -> SettingsOut:
    service.set_setting(db, "ai_enabled", "true" if body.ai_enabled else "false")
    return SettingsOut(ai_enabled=body.ai_enabled)


def _muscles(db: Session, now: datetime) -> list[MuscleStateOut]:
    return [
        MuscleStateOut(**{k: getattr(s, k) for k in MuscleStateOut.model_fields})
        for s in service.muscle_states(db, now)
    ]


@router.get("/muscles", response_model=list[MuscleStateOut])
def muscles(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> list[MuscleStateOut]:
    return _muscles(db, now)


class Ring(BaseModel):
    value: float
    target: float
    label: str
    is_estimate: bool = False


class Dashboard(BaseModel):
    date: str
    has_profile: bool
    rings: dict[str, Ring]
    nutrition: Totals
    game: GameSummary
    muscles: list[MuscleStateOut]


@router.get("/dashboard", response_model=Dashboard)
def dashboard(
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> Dashboard:
    today = now.date()
    profile = service.get_profile(db)
    targets = service.energy_for(profile) if profile else None
    totals = nutrition.day_totals(db, today)
    g = game.summary(db, bus, now)

    burned = 0.0
    if profile:
        for w in db.query(Workout).filter(Workout.day == today).all():
            dur = ((w.finished_at - w.started_at).total_seconds() / 60) if w.finished_at else None
            burned += energy.strength_kcal(
                energy.session_minutes(dur, len(w.sets)), profile.weight_kg
            )

    done = sum(1 for q in g.quest if q.completed_at)
    return Dashboard(
        date=today.isoformat(),
        has_profile=profile is not None,
        rings={
            "tasks": Ring(value=done, target=max(1, len(g.quest)), label="Quest tasks"),
            "kcal_in": Ring(
                value=totals.kcal,
                target=targets.kcal_target if targets else 2000,
                label="kcal eaten",
                is_estimate=True,
            ),
            "kcal_out": Ring(
                value=round(burned),
                target=energy.DEFAULT_BURN_TARGET_KCAL,
                label="kcal burned (training)",
                is_estimate=True,
            ),
        },
        nutrition=totals,
        game=g,
        muscles=_muscles(db, now),
    )


@router.get("/history", response_model=list[history.HistoryDay])
def get_history(
    days: int = 30, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> list[history.HistoryDay]:
    return history.history(db, now, max(1, min(days, 365)))


@router.get("/export/json")
def export_json(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> dict[str, Any]:
    return history.export_json(db, now)


@router.get("/export/csv/{kind}")
def export_csv(kind: Literal["workouts", "meals"], db: Session = Depends(get_db)) -> Response:
    return Response(
        content=history.export_csv(db, kind),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ascend-{kind}.csv"'},
    )
