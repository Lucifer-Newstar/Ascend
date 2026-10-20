from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.workouts import service
from app.modules.workouts.schemas import (
    ExerciseOut,
    FinishedWorkout,
    LoggedSet,
    MuscleWeight,
    SetIn,
    WorkoutOut,
    WorkoutSummary,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])
exercises_router = APIRouter(prefix="/exercises", tags=["workouts"])


@exercises_router.get("", response_model=list[ExerciseOut])
def list_exercises(q: str = "", db: Session = Depends(get_db)) -> list[ExerciseOut]:
    return [
        ExerciseOut(
            id=e.id,
            name=e.name,
            equipment=e.equipment,
            muscles=[
                MuscleWeight(muscle=m.muscle, weight=m.weight)
                for m in sorted(e.muscles, key=lambda m: -m.weight)
            ],
        )
        for e in service.list_exercises(db, q)
    ]


@router.post("", response_model=WorkoutOut, status_code=201)
def start(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> WorkoutOut:
    existing = service.active_workout(db)
    workout = existing or service.start_workout(db, now)
    return service.workout_out(workout)


@router.get("", response_model=list[WorkoutSummary])
def list_workouts(
    limit: int = Query(default=20, ge=1, le=100),
    before: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[WorkoutSummary]:
    """Newest first. Pass the last item's started_at as `before` for the next page."""
    return service.list_workouts(db, limit=limit, before=before)


@router.get("/active", response_model=WorkoutOut | None)
def active(db: Session = Depends(get_db)) -> WorkoutOut | None:
    w = service.active_workout(db)
    return service.workout_out(w) if w else None


@router.get("/{workout_id}", response_model=WorkoutOut)
def get(workout_id: int, db: Session = Depends(get_db)) -> WorkoutOut:
    try:
        return service.workout_out(service.get_workout(db, workout_id))
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{workout_id}/sets", response_model=LoggedSet, status_code=201)
def log_set(
    workout_id: int,
    body: SetIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> LoggedSet:
    try:
        row, previous = service.log_set(db, bus, workout_id, body, now)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Conflict as e:
        raise HTTPException(409, str(e)) from e
    xp = game.xp_for_refs(db, sources=("set", "pr"), ref_id=row.id)
    return LoggedSet(set=service.set_out(row), xp_awarded=xp, previous_best_e1rm=previous)


@router.post("/{workout_id}/finish", response_model=FinishedWorkout)
def finish(
    workout_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> FinishedWorkout:
    try:
        workout, minutes, hard = service.finish_workout(db, bus, workout_id, now)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Conflict as e:
        raise HTTPException(409, str(e)) from e
    xp = game.xp_for_refs(db, sources=("session",), ref_id=workout.id)
    return FinishedWorkout(
        workout=service.workout_out(workout), xp_awarded=xp, active_minutes=minutes, hard_sets=hard
    )
