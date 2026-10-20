"""Per-muscle activity over a window of 1 to 30 days (the muscle map's hover card).

A read model over muscle_load_events joined to the logged sets:

* ``sets``: effective sets, the same weighted figure the recovery status uses
  (primary movers count 1, secondary movers their share);
* ``volume_kg``: lifting volume load (weight x reps) attributed by the exercise's
  muscle share, so a 100 kg x 5 bench adds 500 kg to chest and 150 kg to triceps
  when triceps carry a 0.3 share. Time-based sets add no volume;
* ``last_trained``: when the muscle was last loaded, looking back up to 28 days,
  so the card can say "5 days ago" even in the 1-day view.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.progress.models import MuscleLoadEvent
from app.modules.progress.taxonomy import MUSCLES
from app.modules.workouts.models import WorkoutSet

LOOKBACK_DAYS = 28


class MuscleActivity(BaseModel):
    key: str
    sets: float
    volume_kg: float
    last_trained: datetime | None


def muscle_activity(db: Session, days: int, now: datetime) -> list[MuscleActivity]:
    """One row per muscle in taxonomy order, including muscles with no activity."""
    window_start = datetime.combine(now.date() - timedelta(days=days - 1), time.min)
    since = min(window_start, now - timedelta(days=LOOKBACK_DAYS))
    rows = db.execute(
        select(MuscleLoadEvent, WorkoutSet)
        .join(WorkoutSet, WorkoutSet.id == MuscleLoadEvent.set_id)
        .where(MuscleLoadEvent.at >= since, MuscleLoadEvent.at <= now)
    ).all()

    shares: dict[int, dict[str, float]] = {}
    sets: dict[str, float] = {}
    volume: dict[str, float] = {}
    last: dict[str, datetime] = {}
    for event, s in rows:
        if event.muscle not in last or event.at > last[event.muscle]:
            last[event.muscle] = event.at
        if event.at < window_start:
            continue
        sets[event.muscle] = sets.get(event.muscle, 0.0) + event.es
        if s.duration_s is None and s.weight_kg > 0 and s.reps > 0:
            if s.exercise_id not in shares:
                shares[s.exercise_id] = {m.muscle: m.weight for m in s.exercise.muscles}
            share = shares[s.exercise_id].get(event.muscle, 0.0)
            volume[event.muscle] = volume.get(event.muscle, 0.0) + s.weight_kg * s.reps * share

    return [
        MuscleActivity(
            key=m.key,
            sets=round(sets.get(m.key, 0.0), 1),
            volume_kg=round(volume.get(m.key, 0.0)),
            last_trained=last.get(m.key),
        )
        for m in MUSCLES
    ]
