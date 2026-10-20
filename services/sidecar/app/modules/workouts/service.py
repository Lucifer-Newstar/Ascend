"""Workout logging use-cases. Side effects (XP, muscle load, quests) happen in
event handlers owned by other modules, never here."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetDeleted, SetLogged, SetUpdated, WorkoutLogged
from app.modules.gamification.formulas import HARD_SET_RPE
from app.modules.workouts import pr
from app.modules.workouts.models import Exercise, Workout, WorkoutSet
from app.modules.workouts.schemas import SetIn, SetOut, SetPatch, WorkoutOut, WorkoutSummary


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def list_exercises(db: Session, q: str = "", section: str | None = None) -> list[Exercise]:
    stmt = select(Exercise).order_by(Exercise.name)
    if q:
        stmt = stmt.where(Exercise.name.ilike(f"%{q}%"))
    if section:
        stmt = stmt.where(Exercise.section == section)
    return list(db.scalars(stmt).all())


def set_out(s: WorkoutSet) -> SetOut:
    return SetOut(
        id=s.id,
        exercise_id=s.exercise_id,
        exercise_name=s.exercise.name,
        weight_kg=s.weight_kg,
        reps=s.reps,
        rpe=s.rpe,
        e1rm=s.e1rm,
        is_pr=s.is_pr,
        performed_at=s.performed_at,
    )


def workout_out(w: Workout) -> WorkoutOut:
    return WorkoutOut(
        id=w.id,
        day=w.day,
        started_at=w.started_at,
        finished_at=w.finished_at,
        sets=[set_out(s) for s in w.sets],
    )


def start_workout(db: Session, now: datetime) -> Workout:
    workout = Workout(day=now.date(), started_at=now)
    db.add(workout)
    db.flush()
    return workout


def active_workout(db: Session) -> Workout | None:
    stmt = select(Workout).where(Workout.finished_at.is_(None)).order_by(Workout.id.desc())
    return db.scalars(stmt).first()


def get_workout(db: Session, workout_id: int) -> Workout:
    workout = db.get(Workout, workout_id)
    if workout is None:
        raise NotFound(f"workout {workout_id} not found")
    return workout


def best_e1rm(db: Session, exercise_id: int) -> float | None:
    return db.scalar(select(func.max(WorkoutSet.e1rm)).where(WorkoutSet.exercise_id == exercise_id))


def log_set(
    db: Session, bus: EventBus, workout_id: int, data: SetIn, now: datetime
) -> tuple[WorkoutSet, float | None]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    if db.get(Exercise, data.exercise_id) is None:
        raise NotFound(f"exercise {data.exercise_id} not found")

    e1rm = pr.e1rm_or_none(data.weight_kg, data.reps)
    previous = best_e1rm(db, data.exercise_id)
    row = WorkoutSet(
        workout_id=workout.id,
        exercise_id=data.exercise_id,
        weight_kg=data.weight_kg,
        reps=data.reps,
        rpe=data.rpe,
        e1rm=e1rm,
        is_pr=pr.is_new_pr(e1rm, previous),
        performed_at=now,
    )
    db.add(row)
    db.flush()
    bus.publish(
        db,
        SetLogged(
            set_id=row.id,
            workout_id=workout.id,
            exercise_id=row.exercise_id,
            weight_kg=row.weight_kg,
            reps=row.reps,
            rpe=row.rpe,
            performed_at=now,
            is_pr=row.is_pr,
        ),
    )
    db.refresh(row)
    return row, previous


def finish_workout(
    db: Session, bus: EventBus, workout_id: int, now: datetime
) -> tuple[Workout, float, int]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    if not workout.sets:
        raise Conflict("log at least one set before finishing")
    workout.finished_at = now
    minutes = min(180.0, (now - workout.started_at).total_seconds() / 60)
    hard = sum(1 for s in workout.sets if s.rpe is None or s.rpe >= HARD_SET_RPE)
    db.flush()
    bus.publish(
        db,
        WorkoutLogged(
            workout_id=workout.id, day=workout.day, hard_sets=hard, active_minutes=round(minutes, 1)
        ),
    )
    return workout, round(minutes, 1), hard


def list_workouts(
    db: Session, limit: int = 20, before: datetime | None = None
) -> list[WorkoutSummary]:
    """Finished and active workouts, newest first. `before` is the started_at of the
    last item on the previous page (keyset pagination: stable while new rows arrive)."""
    from app.modules.gamification import service as game

    stmt = select(Workout).order_by(Workout.started_at.desc(), Workout.id.desc()).limit(limit)
    if before is not None:
        stmt = stmt.where(Workout.started_at < before)
    out: list[WorkoutSummary] = []
    for w in db.scalars(stmt).all():
        xp = game.xp_for_refs(db, sources=("session",), ref_id=w.id) + sum(
            game.xp_for_refs(db, sources=("set", "pr"), ref_id=s.id) for s in w.sets
        )
        out.append(
            WorkoutSummary(
                id=w.id,
                day=w.day,
                started_at=w.started_at,
                finished_at=w.finished_at,
                sets=len(w.sets),
                volume_kg=round(sum(s.weight_kg * s.reps for s in w.sets), 1),
                xp=xp,
            )
        )
    return out


def _get_set(db: Session, workout_id: int, set_id: int) -> WorkoutSet:
    row = db.get(WorkoutSet, set_id)
    if row is None or row.workout_id != workout_id:
        raise NotFound(f"set {set_id} not found in workout {workout_id}")
    return row


def recompute_prs(db: Session, exercise_id: int) -> None:
    """Re-derive e1RM and the PR flag for every set of one exercise, oldest first.

    Needed after an edit or delete: fixing a typo (100 kg instead of 10 kg) must
    also clear the false PR it created and restore later PRs it masked.
    """
    rows = db.scalars(
        select(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise_id)
        .order_by(WorkoutSet.performed_at, WorkoutSet.id)
    ).all()
    best: float | None = None
    for row in rows:
        row.e1rm = pr.e1rm_or_none(row.weight_kg, row.reps)
        row.is_pr = pr.is_new_pr(row.e1rm, best)
        if row.e1rm is not None and (best is None or row.e1rm > best):
            best = row.e1rm


def update_set(
    db: Session, bus: EventBus, workout_id: int, set_id: int, patch: SetPatch
) -> WorkoutSet:
    row = _get_set(db, workout_id, set_id)
    changes = patch.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key in ("weight_kg", "reps") and value is None:
            continue  # cannot null a required field; ignore
        setattr(row, key, value)
    db.flush()
    recompute_prs(db, row.exercise_id)
    db.flush()
    bus.publish(
        db,
        SetUpdated(
            set_id=row.id,
            workout_id=row.workout_id,
            exercise_id=row.exercise_id,
            weight_kg=row.weight_kg,
            reps=row.reps,
            rpe=row.rpe,
            performed_at=row.performed_at,
        ),
    )
    db.refresh(row)
    return row


def delete_set(db: Session, bus: EventBus, workout_id: int, set_id: int) -> None:
    row = _get_set(db, workout_id, set_id)
    exercise_id = row.exercise_id
    bus.publish(db, SetDeleted(set_id=row.id, workout_id=workout_id, exercise_id=exercise_id))
    db.delete(row)
    db.flush()
    recompute_prs(db, exercise_id)
