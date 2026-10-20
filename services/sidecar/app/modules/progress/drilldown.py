"""Muscle drill-down (1 day to 1 month) and weekly training summaries.

Both are read models over data other modules already wrote: muscle_load_events
(progress), workout sets (workouts), XP (gamification) and meals (nutrition).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.progress import muscle_load
from app.modules.progress.models import MuscleLoadEvent
from app.modules.progress.taxonomy import MUSCLES
from app.modules.workouts.models import WorkoutSet

MUSCLE_BY_KEY = {m.key: m for m in MUSCLES}


class UnknownMuscle(Exception):
    pass


class MuscleDay(BaseModel):
    day: date
    eff_sets: float
    readiness: float


class ContributingSet(BaseModel):
    set_id: int
    at: datetime
    exercise: str
    weight: float
    effort: float
    es: float


class MuscleHistory(BaseModel):
    code: str
    label: str
    days: int
    status: str
    es_7d: float
    target_low: float
    target_high: float
    readiness: float
    ready_at: datetime | None
    daily: list[MuscleDay]
    contributing_sets: list[ContributingSet]
    suggestion: str | None
    formula_version: str


def _suggestion(state: muscle_load.MuscleState) -> str | None:
    if state.status == "under":
        gap = max(1, round(state.weekly_low - state.es_7d))
        return f"About {gap} more hard sets this week reaches the {state.weekly_low:g}-set minimum."
    if state.status == "over":
        return "Weekly volume is well above the target range; keep the next sessions lighter."
    if state.status == "recovering" and state.ready_at is not None:
        return f"Still recovering; fully ready around {state.ready_at:%a %H:%M}."
    if state.status == "optimal":
        return "In the target range. Keep the current plan."
    return None


def muscle_history(db: Session, code: str, days: int, now: datetime) -> MuscleHistory:
    muscle = MUSCLE_BY_KEY.get(code)
    if muscle is None:
        raise UnknownMuscle(code)
    first_day = now.date() - timedelta(days=days - 1)
    # 28 extra days of history so readiness on the first day includes earlier fatigue.
    since = datetime.combine(first_day, time.min) - timedelta(days=28)
    rows = db.execute(
        select(MuscleLoadEvent, WorkoutSet)
        .join(WorkoutSet, WorkoutSet.id == MuscleLoadEvent.set_id)
        .where(MuscleLoadEvent.muscle == code, MuscleLoadEvent.at >= since)
        .order_by(MuscleLoadEvent.at)
    ).all()
    contribs = [muscle_load.Contribution(e.muscle, e.es, e.at) for e, _ in rows]

    def state_at(at: datetime) -> muscle_load.MuscleState:
        return next(s for s in muscle_load.compute_states(contribs, at) if s.key == code)

    daily: list[MuscleDay] = []
    for i in range(days):
        d = first_day + timedelta(days=i)
        end = min(now, datetime.combine(d, time.max).replace(microsecond=0))
        es = sum(c.es for c in contribs if c.at.date() == d)
        daily.append(MuscleDay(day=d, eff_sets=round(es, 2), readiness=state_at(end).readiness))

    window_start = datetime.combine(first_day, time.min)
    mapping = {}
    contributing: list[ContributingSet] = []
    for event, s in reversed(rows):
        if event.at < window_start:
            continue
        if s.exercise_id not in mapping:
            mapping[s.exercise_id] = {m.muscle: m.weight for m in s.exercise.muscles}
        weight = mapping[s.exercise_id].get(code, 0.0)
        contributing.append(
            ContributingSet(
                set_id=s.id,
                at=event.at,
                exercise=s.exercise.name,
                weight=weight,
                effort=round(event.es / weight, 3) if weight else 0.0,
                es=event.es,
            )
        )
    current = state_at(now)
    return MuscleHistory(
        code=code,
        label=muscle.label,
        days=days,
        status=current.status,
        es_7d=current.es_7d,
        target_low=muscle.weekly_low,
        target_high=muscle.weekly_high,
        readiness=current.readiness,
        ready_at=current.ready_at,
        daily=daily,
        contributing_sets=contributing,
        suggestion=_suggestion(current),
        formula_version=muscle_load.FORMULA_VERSION,
    )
