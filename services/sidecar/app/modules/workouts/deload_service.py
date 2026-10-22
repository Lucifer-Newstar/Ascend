"""Collects the deload engine's inputs from the workouts, progress and
check-in read models, and records an accepted deload week."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.intelligence import progression_service
from app.modules.progress import checkins
from app.modules.progress import service as progress
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from app.modules.workouts import deload
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

DELOAD_SETTING = "deload_week"
HISTORY_WEEKS = 8


class SignalOut(BaseModel):
    code: str
    active: bool
    detail: str


class DeloadOut(BaseModel):
    recommended: bool
    kind: str
    training_weeks: int
    signals: list[SignalOut]
    guidance: str | None
    deload_week: date | None
    algo_version: str


def _last_deload_week(db: Session) -> date | None:
    raw = progress.get_setting(db, DELOAD_SETTING, "")
    return date.fromisoformat(raw) if raw else None


def _weekly_sessions(db: Session, today: date, since: date | None) -> list[int]:
    this_week = deload.week_start(today)
    first = this_week - timedelta(weeks=HISTORY_WEEKS)
    if since is not None:
        first = max(first, since + timedelta(weeks=1))
    days = db.scalars(
        select(Workout.day).where(
            Workout.finished_at.is_not(None), Workout.day >= first, Workout.day < this_week
        )
    ).all()
    weeks: list[int] = []
    cursor = first
    while cursor < this_week:
        weeks.append(sum(1 for d in days if cursor <= d < cursor + timedelta(days=7)))
        cursor += timedelta(days=7)
    return weeks


def _best(db: Session, exercise_id: int, start: datetime, end: datetime) -> float | None:
    value = db.scalar(
        select(func.max(WorkoutSet.e1rm)).where(
            WorkoutSet.exercise_id == exercise_id,
            WorkoutSet.performed_at >= start,
            WorkoutSet.performed_at < end,
        )
    )
    return float(value) if value is not None else None


def _lift_trends(db: Session, now: datetime) -> list[deload.LiftTrend]:
    recent_start = now - timedelta(days=14)
    prev_start = recent_start - timedelta(days=21)
    trends: list[deload.LiftTrend] = []
    for name in deload.KEY_LIFTS:
        ex = db.scalars(select(Exercise).where(Exercise.name == name)).first()
        if ex is None:
            continue
        trends.append(
            deload.LiftTrend(
                name=name,
                recent_best=_best(db, ex.id, recent_start, now + timedelta(seconds=1)),
                previous_best=_best(db, ex.id, prev_start, recent_start),
            )
        )
    return trends


def advice(db: Session, now: datetime) -> DeloadOut:
    today = now.date()
    last = _last_deload_week(db)
    recent = checkins.recent(db, today, 7)
    # Counted per v7 region (chest, quads...), not per head: under taxonomy v2 one tired
    # quadriceps is four heads, and the threshold of 3 was set for regions (ADR-0021).
    strained = len(
        {
            MUSCLE_BY_KEY[m.key].legacy if m.key in MUSCLE_BY_KEY else m.key
            for m in progress.muscle_states(db, now)
            if (m.status == "over" or (m.status != "no_data" and m.readiness < 0.5))
            and not (m.key in MUSCLE_BY_KEY and MUSCLE_BY_KEY[m.key].readiness_only)
        }
    )
    inputs = deload.DeloadInputs(
        weekly_sessions=_weekly_sessions(db, today, last),
        readiness_7d=[c.readiness for c in recent],
        soreness_7d=[c.soreness for c in recent],
        lifts=_lift_trends(db, datetime.combine(today, time.max).replace(microsecond=0)),
        strained_muscles=strained,
        in_deload_week=last == deload.week_start(today),
        stalled_lifts=[e.name for e, _ in progression_service.stalled_lifts(db, now)],
    )
    a = deload.advise(inputs)
    return DeloadOut(
        recommended=a.recommended,
        kind=a.kind,
        training_weeks=a.training_weeks,
        signals=[SignalOut(code=s.code, active=s.active, detail=s.detail) for s in a.signals],
        guidance=a.guidance,
        deload_week=last,
        algo_version=a.algo_version,
    )


def start_deload_week(db: Session, now: datetime) -> DeloadOut:
    """The user accepted the deload: this Monday-start week is the deload week."""
    progress.set_setting(db, DELOAD_SETTING, deload.week_start(now.date()).isoformat())
    db.flush()
    return advice(db, now)
