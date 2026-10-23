"""Planner endpoints: goal checks, workout programs and meal plans (ADR-0023)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.planner import service
from app.modules.planner.schemas import (
    CustomProgramOut,
    DietPlanIn,
    DietPlanOut,
    DietSaveIn,
    GoalCheckIn,
    GoalCheckOut,
    ProgramDraft,
    SavedDietOut,
    WorkoutPlanIn,
    WorkoutPlanOut,
)
from app.modules.progress import service as progress
from app.modules.workouts import programs_service

router = APIRouter(prefix="/planner", tags=["planner"])


@router.post("/check", response_model=GoalCheckOut)
def check(body: GoalCheckIn, db: Session = Depends(get_db)) -> GoalCheckOut:
    """goalcheck-v1: flag unrealistic or unsafe goals (each flag with its numbers). Without a
    height in the request, the profile's height is used."""
    if body.height_cm is None:
        p = progress.get_profile(db)
        if p is not None:
            body = body.model_copy(update={"height_cm": p.height_cm})
    return service.check(body)


@router.post("/workout", response_model=WorkoutPlanOut)
def draft_workout(
    body: WorkoutPlanIn, request: Request, db: Session = Depends(get_db)
) -> WorkoutPlanOut:
    """Draft a custom program (plangen-v1). Nothing is saved."""
    return service.draft_workout(db, request.app.state.settings, body)


@router.get("/programs", response_model=list[CustomProgramOut])
def list_programs(db: Session = Depends(get_db)) -> list[CustomProgramOut]:
    return service.list_programs(db)


@router.post("/programs", response_model=CustomProgramOut, status_code=201)
def save_program(
    body: ProgramDraft, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> CustomProgramOut:
    """Save a (possibly edited) draft. Every exercise must be in the library."""
    try:
        return service.save_program(db, body, now)
    except ValueError as e:
        raise HTTPException(422, f"unknown exercise or bad range: {e}") from e


@router.put("/programs/{program_id}", response_model=CustomProgramOut)
def update_program(
    program_id: int,
    body: ProgramDraft,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> CustomProgramOut:
    try:
        return service.update_program(db, program_id, body, now)
    except service.NotFound as e:
        raise HTTPException(404, "program not found") from e
    except ValueError as e:
        raise HTTPException(422, f"unknown exercise or bad range: {e}") from e


@router.delete("/programs/{program_id}", status_code=204)
def delete_program(
    program_id: int, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> Response:
    try:
        service.delete_program(db, program_id, now)
    except service.NotFound as e:
        raise HTTPException(404, "program not found") from e
    return Response(status_code=204)


@router.post("/programs/{program_id}/follow", response_model=CustomProgramOut)
def follow_program(
    program_id: int, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> CustomProgramOut:
    """Follow a saved program (it becomes the plan on Today and Train)."""
    try:
        programs_service.enroll(db, f"{service.CUSTOM_PREFIX}{program_id}", now)
    except programs_service.UnknownProgram as e:
        raise HTTPException(404, "program not found") from e
    return next(p for p in service.list_programs(db) if p.id == program_id)


@router.post("/diet", response_model=DietPlanOut)
def draft_diet(body: DietPlanIn, request: Request, db: Session = Depends(get_db)) -> DietPlanOut:
    """Draft a 7-day meal plan (dietgen-v1) from the energy targets. Nothing is saved."""
    try:
        return service.draft_diet(db, request.app.state.settings, body)
    except service.NoProfile as e:
        raise HTTPException(409, "set up your profile first") from e


@router.get("/diets", response_model=list[SavedDietOut])
def list_diets(db: Session = Depends(get_db)) -> list[SavedDietOut]:
    return service.list_diets(db)


@router.post("/diets", response_model=SavedDietOut, status_code=201)
def save_diet(
    body: DietSaveIn, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> SavedDietOut:
    """Save a meal plan; it becomes the active one."""
    return service.save_diet(db, body.name, body.plan, now)


@router.delete("/diets/{diet_id}", status_code=204)
def delete_diet(diet_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        service.delete_diet(db, diet_id)
    except service.NotFound as e:
        raise HTTPException(404, "diet plan not found") from e
    return Response(status_code=204)
