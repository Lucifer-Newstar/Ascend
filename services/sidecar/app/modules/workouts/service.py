"""Workout logging use-cases. Side effects (XP, muscle load, quests) happen in
event handlers owned by other modules, never here."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, SetLogged, WorkoutLogged
from app.modules.gamification.formulas import HARD_SET_RPE
from app.modules.workouts import pr
from app.modules.workouts.models import Exercise, Workout, WorkoutSet
from app.modules.workouts.schemas import SetIn, SetOut, WorkoutOut


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def list_exercises(db: Session, q: str = "") -> list[Exercise]:
    stmt = select(Exercise).order_by(Exercise.name)
    if q:
        stmt = stmt.where(Exercise.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt).all())


def set_out(s: WorkoutSet) -> SetOut:
    return SetOut(
        id=s.id, exercise_id=s.exercise_id, exercise_name=s.exercise.name,
        weight_kg=s.weight_kg, reps=s.reps, rpe=s.rpe, e1rm=s.e1rm, is_pr=s.is_pr,
        performed_at=s.performed_at,
    )


def workout_out(w: Workout) -> WorkoutOut:
    return WorkoutOut(id=w.id, day=w.day, started_at=w.started_at, finished_at=w.finished_at,
                      sets=[set_out(s) for s in w.sets])


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


def log_set(db: Session, bus: EventBus, workout_id: int, data: SetIn, now: datetime) -> tuple[WorkoutSet, float | None]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    if db.get(Exercise, data.exercise_id) is None:
        raise NotFound(f"exercise {data.exercise_id} not found")

    e1rm = pr.e1rm_or_none(data.weight_kg, data.reps)
    previous = best_e1rm(db, data.exercise_id)
    row = WorkoutSet(
        workout_id=workout.id, exercise_id=data.exercise_id, weight_kg=data.weight_kg,
        reps=data.reps, rpe=data.rpe, e1rm=e1rm, is_pr=pr.is_new_pr(e1rm, previous),
        performed_at=now,
    )
    db.add(row)
    db.flush()
    bus.publish(db, SetLogged(
        set_id=row.id, workout_id=workout.id, exercise_id=row.exercise_id,
        weight_kg=row.weight_kg, reps=row.reps, rpe=row.rpe, performed_at=now, is_pr=row.is_pr,
    ))
    db.refresh(row)
    return row, previous


def finish_workout(db: Session, bus: EventBus, workout_id: int, now: datetime) -> tuple[Workout, float, int]:
    workout = get_workout(db, workout_id)
    if workout.finished_at is not None:
        raise Conflict("workout already finished")
    if not workout.sets:
        raise Conflict("log at least one set before finishing")
    workout.finished_at = now
    minutes = min(180.0, (now - workout.started_at).total_seconds() / 60)
    hard = sum(1 for s in workout.sets if s.rpe is None or s.rpe >= HARD_SET_RPE)
    db.flush()
    bus.publish(db, WorkoutLogged(workout_id=workout.id, day=workout.day, hard_sets=hard,
                                  active_minutes=round(minutes, 1)))
    return workout, round(minutes, 1), hard
