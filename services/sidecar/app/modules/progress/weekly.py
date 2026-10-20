"""Weekly training summary for the Progress charts (Monday-start weeks)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.gamification.models import XpEvent
from app.modules.nutrition.service import day_totals
from app.modules.progress.models import BodyMetric
from app.modules.workouts.activity_seed import TIME_BASED_SECTIONS
from app.modules.workouts.models import Workout


class WeekSummary(BaseModel):
    week_start: date
    sessions: int
    sets: int
    volume_kg: float
    active_minutes: float
    xp: int
    avg_kcal_in: float | None
    avg_weight_kg: float | None


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def weekly(db: Session, now: datetime, weeks: int) -> list[WeekSummary]:
    """Oldest week first; the current (partial) week is included last."""
    this_week = monday(now.date())
    first = this_week - timedelta(weeks=weeks - 1)
    out: list[WeekSummary] = []
    workouts = db.scalars(select(Workout).where(Workout.day >= first)).all()
    xps = db.scalars(select(XpEvent).where(XpEvent.day >= first)).all()
    metrics = db.scalars(
        select(BodyMetric).where(
            BodyMetric.measured_at >= datetime.combine(first, datetime.min.time())
        )
    ).all()
    for i in range(weeks):
        start = first + timedelta(weeks=i)
        end = start + timedelta(days=7)
        ws = [w for w in workouts if start <= w.day < end]
        sets = [s for w in ws for s in w.sets]
        lifting = [s for s in sets if s.exercise.section not in TIME_BASED_SECTIONS]
        minutes = 0.0
        for w in ws:
            if w.finished_at:
                minutes += min(180.0, (w.finished_at - w.started_at).total_seconds() / 60)
        days_so_far = [
            start + timedelta(days=k) for k in range(7) if start + timedelta(days=k) <= now.date()
        ]
        kcal_days = [t.kcal for t in (day_totals(db, d) for d in days_so_far) if t.kcal > 0]
        weights = [m.weight_kg for m in metrics if start <= m.measured_at.date() < end]
        out.append(
            WeekSummary(
                week_start=start,
                sessions=sum(1 for w in ws if w.finished_at),
                sets=len(sets),
                volume_kg=round(sum(s.weight_kg * s.reps for s in lifting), 1),
                active_minutes=round(minutes, 1),
                xp=sum(x.amount for x in xps if start <= x.day < end),
                avg_kcal_in=round(sum(kcal_days) / len(kcal_days), 1) if kcal_days else None,
                avg_weight_kg=round(sum(weights) / len(weights), 2) if weights else None,
            )
        )
    return out
