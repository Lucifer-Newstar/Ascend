from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.gamification.schemas import GameSummary
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.schemas import Totals
from app.modules.progress import body, checkins, drilldown, energy, history, service, weekly
from app.modules.progress.schemas import (
    BodyMetricIn,
    BodyMetricOut,
    CheckinIn,
    CheckinOut,
    EtaOut,
    MeasurementIn,
    MeasurementOut,
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
    fields = (
        "name",
        "age",
        "sex",
        "height_cm",
        "weight_kg",
        "goal",
        "activity",
        "target_weight_kg",
    )
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
    return service.read_settings(db)


@router.put("/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, db: Session = Depends(get_db)) -> SettingsOut:
    """Partial update; omitted fields keep their stored value."""
    return service.update_settings(db, body)


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
            burned += service.workout_burn(w, profile.weight_kg)

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
                label="kcal burned (training + activities)",
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


# --- body metrics -----------------------------------------------------------------


@router.get("/body-metrics", response_model=list[BodyMetricOut])
def list_body_metrics(
    days: int = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[BodyMetricOut]:
    """Weigh-ins in the last `days`, oldest first, each with its trend weight."""
    return body.list_metrics(db, now, days)


@router.post("/body-metrics", response_model=BodyMetricOut, status_code=201)
def log_body_metric(
    body_in: BodyMetricIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> BodyMetricOut:
    """Log a weigh-in. The newest weigh-in also becomes the profile weight, so the
    calorie estimate follows the user's real weight."""
    out = body.log_metric(db, body_in, now)
    profile = service.get_profile(db)
    newest = body.list_metrics(db, now, 3650)
    if profile is not None and newest and newest[-1].id == out.id:
        profile.weight_kg = out.weight_kg
    return out


@router.delete("/body-metrics/{metric_id}", status_code=204)
def delete_body_metric(metric_id: int, db: Session = Depends(get_db)) -> Response:
    if not body.delete_metric(db, metric_id):
        raise HTTPException(404, f"body metric {metric_id} not found")
    return Response(status_code=204)


@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurements(
    site: str | None = None, db: Session = Depends(get_db)
) -> list[MeasurementOut]:
    return body.list_measurements(db, site)


@router.post("/measurements", response_model=MeasurementOut, status_code=201)
def log_measurement(
    body_in: MeasurementIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> MeasurementOut:
    return body.log_measurement(db, body_in, now)


@router.get("/progress/eta", response_model=EtaOut)
def progress_eta(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> EtaOut:
    """Estimated date range to reach the profile's target weight."""
    profile = service.get_profile(db)
    return body.eta_for(db, profile.target_weight_kg if profile else None, now)


@router.get("/muscles/{code}/history", response_model=drilldown.MuscleHistory)
def muscle_history(
    code: str,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> drilldown.MuscleHistory:
    """Drill-down for one muscle: daily effective sets and readiness for 1-30 days,
    the sets that loaded it, and a plain-language suggestion from the status rules."""
    try:
        return drilldown.muscle_history(db, code, days, now)
    except drilldown.UnknownMuscle as e:
        raise HTTPException(404, f"unknown muscle '{code}'") from e


@router.get("/progress/weekly", response_model=list[weekly.WeekSummary])
def progress_weekly(
    weeks: int = Query(default=8, ge=1, le=52),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[weekly.WeekSummary]:
    """Per-week sessions, sets, lifting volume, minutes, XP, average intake and weight."""
    return weekly.weekly(db, now, weeks)


# --- readiness check-in -------------------------------------------------------------


@router.post("/checkins", response_model=CheckinOut, status_code=201)
def post_checkin(
    body_in: CheckinIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> CheckinOut:
    """20-second morning check-in. Re-submitting the same day replaces the answer."""
    return checkins.record(db, bus, body_in, now)


@router.get("/checkins/today", response_model=CheckinOut | None)
def checkin_today(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> CheckinOut | None:
    return checkins.for_day(db, now.date())


@router.get("/checkins", response_model=list[CheckinOut])
def list_checkins(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> list[CheckinOut]:
    return checkins.recent(db, now.date(), days)
