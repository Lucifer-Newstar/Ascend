from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.workouts import deload_service, service
from app.modules.workouts.activity_seed import SECTIONS, TIME_BASED_SECTIONS
from app.modules.workouts.schemas import (
    ExerciseOut,
    FinishedWorkout,
    LoggedSet,
    MuscleWeight,
    PROut,
    SetIn,
    SetOut,
    SetPatch,
    WorkoutOut,
    WorkoutSummary,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])
exercises_router = APIRouter(prefix="/exercises", tags=["workouts"])
prs_router = APIRouter(prefix="/prs", tags=["workouts"])
deload_router = APIRouter(prefix="/deload", tags=["workouts"])


@deload_router.get("", response_model=deload_service.DeloadOut)
def deload_advice(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> deload_service.DeloadOut:
    """Is a deload week due? Planned after 3 training weeks, or reactive when 2 of the
    4 fatigue signals hold. Each signal is listed with the numbers behind it."""
    return deload_service.advice(db, now)


@deload_router.post("/start", response_model=deload_service.DeloadOut)
def start_deload(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> deload_service.DeloadOut:
    """Accept the deload: the current week is recorded as the deload week."""
    return deload_service.start_deload_week(db, now)


@prs_router.get("", response_model=list[PROut])
def list_prs(exercise_id: int | None = None, db: Session = Depends(get_db)) -> list[PROut]:
    """Best Epley e1RM per exercise (sets of 1-10 reps with load), highest first."""
    return service.personal_records(db, exercise_id)


@exercises_router.get("", response_model=list[ExerciseOut])
def list_exercises(
    q: str = "", section: str | None = None, db: Session = Depends(get_db)
) -> list[ExerciseOut]:
    if section is not None and section not in SECTIONS:
        raise HTTPException(422, f"unknown section '{section}'")
    return [
        ExerciseOut(
            id=e.id,
            name=e.name,
            equipment=e.equipment,
            section=e.section,
            met=e.met,
            time_based=e.section in TIME_BASED_SECTIONS,
            muscles=[
                MuscleWeight(muscle=m.muscle, weight=m.weight)
                for m in sorted(e.muscles, key=lambda m: -m.weight)
            ],
        )
        for e in service.list_exercises(db, q, section)
    ]


@router.post("", response_model=WorkoutOut, status_code=201)
def start(
    section: str = "gym", db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> WorkoutOut:
    """Start a session (or return the one already running). `section` is a hint; the
    first logged set decides it."""
    if section not in SECTIONS:
        raise HTTPException(422, f"unknown section '{section}'")
    existing = service.active_workout(db)
    workout = existing or service.start_workout(db, now, section)
    return service.workout_out(workout)


@router.get("", response_model=list[WorkoutSummary])
def list_workouts(
    limit: int = Query(default=20, ge=1, le=100),
    before: datetime | None = None,
    section: str | None = None,
    source: Literal["app", "strong", "hevy"] | None = None,
    since: date | None = Query(default=None, description="First day to include"),
    until: date | None = Query(default=None, description="Last day to include"),
    db: Session = Depends(get_db),
) -> list[WorkoutSummary]:
    """Newest first. Pass the last item's started_at as `before` for the next page.
    Optional filters: section, source (app or an import) and a day range."""
    if section is not None and section not in SECTIONS:
        raise HTTPException(422, f"unknown section {section!r}")
    if since and until and since > until:
        raise HTTPException(422, "since must be on or before until")
    return service.list_workouts(
        db,
        limit=limit,
        before=before,
        filters=service.WorkoutFilters(section=section, source=source, since=since, until=until),
    )


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
    except service.Invalid as e:
        raise HTTPException(422, str(e)) from e
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


@router.patch("/{workout_id}/sets/{set_id}", response_model=SetOut)
def edit_set(
    workout_id: int,
    set_id: int,
    body: SetPatch,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
) -> SetOut:
    """Fix a logged set. PRs for the exercise and the set's muscle load are re-derived;
    XP already awarded is kept (the XP ledger is append-only)."""
    try:
        row = service.update_set(db, bus, workout_id, set_id, body)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    return service.set_out(row)


@router.delete("/{workout_id}/sets/{set_id}", status_code=204)
def delete_set(
    workout_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
) -> Response:
    try:
        service.delete_set(db, bus, workout_id, set_id)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=204)
