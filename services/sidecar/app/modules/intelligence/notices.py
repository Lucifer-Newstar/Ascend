"""System notices (ADR-0016): the few moments the System speaks, computed from the
engines' state, at most one of each kind at a time.

  deload     the deload check recommends a deload this week (deload-v2)
  raised     prog-v1 raised a target after your latest session (biggest raise only)
  recovered  a muscle you trained in the last 4 days is ready again and today's quest
             trains it

Each notice has a stable id; the app shows an id once and remembers it, so the System
never repeats itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.intelligence import progression_service, recovery_service
from app.modules.workouts.models import Workout

RAISED_WITHIN = timedelta(hours=36)
RECOVERED_AFTER_TRAINING = timedelta(hours=96)
RECOVERED_READINESS = 0.95
SIGNAL_WORDS = {
    "LOW_READINESS": "low check-in readiness",
    "HEAVY_SORENESS": "heavy soreness",
    "PERFORMANCE_DROP": "falling e1RM on key lifts",
    "FATIGUE_BUILDUP": "fatigue building up in several muscles",
    "STALLED_LIFTS": "stalled lifts",
}


@dataclass(frozen=True)
class Notice:
    id: str
    code: str  # deload | raised | recovered
    title: str
    text: str
    at: datetime


def _deload(db: Session, now: datetime) -> Notice | None:
    from app.modules.workouts import deload, deload_service

    a = deload_service.advice(db, now)
    if not a.recommended:
        return None
    week = deload.week_start(now.date())
    if a.kind == "planned":
        why = f"{a.training_weeks} training weeks in a row"
    else:
        why = " and ".join(SIGNAL_WORDS.get(s.code, s.code) for s in a.signals if s.active)
    return Notice(
        f"deload:{week.isoformat()}",
        "deload",
        "Deload advised",
        f"The System detects {why}. {a.guidance or ''}".strip(),
        now,
    )


def _raised(db: Session, now: datetime) -> Notice | None:
    w = db.scalars(
        select(Workout)
        .where(Workout.finished_at.is_not(None), Workout.finished_at >= now - RAISED_WITHIN)
        .order_by(Workout.finished_at.desc())
        .limit(1)
    ).first()
    if w is None or w.finished_at is None:
        return None
    best: tuple[float, Notice] | None = None
    for ex_id in sorted({s.exercise_id for s in w.sets}):
        try:
            e, t = progression_service.next_target(db, ex_id, now)
        except progression_service.ExerciseMissing:
            continue
        if t.change not in ("up_load", "advance"):
            continue
        last = t.inputs.get("last_load_kg") or t.inputs.get("added_load_kg") or 0
        gain = (t.weight_kg - last) / last if isinstance(last, (int, float)) and last else 0.05
        amount = f"{t.seconds} s" if t.kind == "hold" else f"{t.reps}"
        load = f" @ {t.weight_kg:g} kg" if t.weight_kg else ""
        n = Notice(
            f"raised:{w.id}:{e.id}",
            "raised",
            "Target raised",
            f"{e.name}: next time {t.sets} \u00d7 {amount}{load}. {t.why}",
            w.finished_at,
        )
        if best is None or gain > best[0]:
            best = (gain, n)
    return best[1] if best else None


def _recovered(db: Session, now: datetime) -> Notice | None:
    from app.modules.gamification import service as game

    items = [q for q in game.ensure_quest(db, now) if q.metric.startswith("sets:")]
    if not items:
        return None
    states = {m.key: m for m in recovery_service.states(db, now)}
    for q in items:
        m = states.get(q.metric.split(":", 1)[1])
        if (
            m is not None
            and m.last_trained is not None
            and now - m.last_trained <= RECOVERED_AFTER_TRAINING
            and m.readiness >= RECOVERED_READINESS
        ):
            return Notice(
                f"recovered:{now.date().isoformat()}:{m.key}",
                "recovered",
                "Muscle recovered",
                f"{m.label} is {round(m.readiness * 100)}% recovered. Today's quest: {q.title}.",
                now,
            )
    return None


def current(db: Session, now: datetime) -> list[Notice]:
    return [n for n in (_deload(db, now), _raised(db, now), _recovered(db, now)) if n]
