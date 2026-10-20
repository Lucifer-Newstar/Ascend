"""Recovery-v2 service: loads stored doses, the check-in and the personal factors, runs
the pure engine (recovery.py) and refits the factors (personal.py) after a session."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, WorkoutLogged, WorkoutsImported
from app.modules.intelligence import personal
from app.modules.intelligence import recovery as rec
from app.modules.intelligence.models import RecoveryParam
from app.modules.progress.models import Checkin, MuscleLoadEvent
from app.modules.workouts.models import Exercise, Workout, WorkoutSet

log = logging.getLogger("ascend.recovery")

FIT_DAYS = 365
# A check-in describes the night before and this morning; it modifies today only.
CHECKIN_VALID_H = 18


def personal_k(db: Session) -> dict[str, float]:
    return {r.group: r.k for r in db.scalars(select(RecoveryParam)).all()}


def params(db: Session) -> dict[str, RecoveryParam]:
    return {r.group: r for r in db.scalars(select(RecoveryParam)).all()}


def checkin_for(db: Session, now: datetime) -> rec.CheckinInput | None:
    row = db.scalars(select(Checkin).where(Checkin.day == now.date())).first()
    if row is None or row.created_at > now:
        return None
    if (now - row.created_at).total_seconds() / 3600 > CHECKIN_VALID_H:
        return None
    return rec.CheckinInput(sleep=row.sleep, soreness=row.soreness)


def contributions(db: Session, since: datetime, until: datetime) -> list[rec.Contribution]:
    rows = db.execute(
        select(MuscleLoadEvent.muscle, MuscleLoadEvent.es, MuscleLoadEvent.at, Exercise.name)
        .join(WorkoutSet, WorkoutSet.id == MuscleLoadEvent.set_id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(MuscleLoadEvent.at >= since, MuscleLoadEvent.at <= until)
    ).all()
    return [rec.Contribution(m, es, at, name) for m, es, at, name in rows]


def states(
    db: Session, now: datetime, *, personalised: bool = True, use_checkin: bool = True
) -> list[rec.MuscleRecovery]:
    contribs = contributions(db, now - timedelta(days=rec.LOOKBACK_DAYS), now)
    k = personal_k(db) if personalised else None
    checkin = checkin_for(db, now) if use_checkin else None
    return rec.compute_from(contribs, now, k, checkin)


def states_at_many(
    db: Session, times: Sequence[datetime], muscle: str | None = None
) -> list[list[rec.MuscleRecovery]]:
    """Several points in time with one read (the drill-down's daily series). Past days use
    the personal factors but not a check-in (it only describes its own morning)."""
    if not times:
        return []
    lo, hi = min(times), max(times)
    contribs = contributions(db, lo - timedelta(days=rec.LOOKBACK_DAYS), hi)
    if muscle is not None:
        contribs = [c for c in contribs if c.muscle == muscle]
    k = personal_k(db)
    return [rec.compute_from(contribs, t, k) for t in times]


# --- personalisation ------------------------------------------------------------------


def performances(db: Session, since: datetime, until: datetime) -> list[personal.SessionPerf]:
    """Session-level mean e1RM per lift (personal.session_e1rm) for the fit."""
    rows = db.execute(
        select(
            WorkoutSet.workout_id,
            WorkoutSet.exercise_id,
            WorkoutSet.weight_kg,
            WorkoutSet.reps,
            WorkoutSet.rpe,
            Workout.started_at,
        )
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(
            Workout.started_at >= since,
            Workout.started_at <= until,
            Exercise.measure == "reps",
            WorkoutSet.weight_kg > 0,
            WorkoutSet.duration_s.is_(None),
        )
    ).all()
    by: dict[tuple[int, int], list[tuple[float, int, float | None]]] = {}
    starts: dict[int, datetime] = {}
    for wid, eid, kg, reps, rpe, started in rows:
        by.setdefault((wid, eid), []).append((kg, reps, rpe))
        starts[wid] = started
    ids = {eid for _, eid in by}
    exercises = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(ids))).all()}
    out: list[personal.SessionPerf] = []
    for (wid, eid), sets in by.items():
        e1rm = personal.session_e1rm(sets)
        ex = exercises.get(eid)
        if e1rm is None or ex is None:
            continue
        muscles = {m.muscle: m.weight for m in ex.muscles}
        out.append(personal.SessionPerf(ex.name, starts[wid], e1rm, muscles))
    return out


def refit(db: Session, now: datetime) -> list[personal.GroupFit]:
    """Fit k per muscle group on the last year and store it (replacing earlier rows)."""
    t0 = time.perf_counter()
    since = now - timedelta(days=FIT_DAYS)
    perfs = performances(db, since, now)
    contribs = contributions(db, since - timedelta(hours=personal.LOOKBACK_H), now)
    fits = personal.fit(perfs, contribs)
    existing = params(db)
    for f in fits:
        row = existing.get(f.group)
        if row is None:
            row = RecoveryParam(group=f.group)
            db.add(row)
        row.k, row.k_low, row.k_high = f.k, f.k_low, f.k_high
        row.k_hat, row.alpha, row.n, row.personal = f.k_hat, f.alpha, f.n, f.personal
        row.algo_version = personal.ALGO_VERSION
        row.updated_at = now
    db.flush()
    log.info("recovery refit: %d sessions, %.0f ms", len(perfs), 1000 * (time.perf_counter() - t0))
    return fits


def last_refit(db: Session) -> datetime | None:
    return db.scalar(select(func.max(RecoveryParam.updated_at)))


def on_workout_logged(db: Session, event: WorkoutLogged) -> None:
    w = db.get(Workout, event.workout_id)
    if w is not None and w.finished_at is not None:
        refit(db, w.finished_at)


def on_workouts_imported(db: Session, event: WorkoutsImported) -> None:
    if event.last_day is not None and event.sets:
        latest = db.scalar(select(func.max(WorkoutSet.performed_at)))
        if latest is not None:
            refit(db, latest)


def register(bus: EventBus) -> None:
    bus.subscribe(WorkoutLogged, on_workout_logged)
    bus.subscribe(WorkoutsImported, on_workouts_imported)
