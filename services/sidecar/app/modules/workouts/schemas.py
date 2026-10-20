from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MuscleWeight(BaseModel):
    muscle: str
    weight: float


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    equipment: str
    section: str = "gym"
    met: float | None = None
    time_based: bool = False
    muscles: list[MuscleWeight]


class SetIn(BaseModel):
    exercise_id: int
    weight_kg: float = Field(ge=0, le=500)
    reps: int = Field(ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    exercise_name: str
    weight_kg: float
    reps: int
    rpe: float | None
    e1rm: float | None
    is_pr: bool
    performed_at: datetime


class LoggedSet(BaseModel):
    set: SetOut
    xp_awarded: int
    previous_best_e1rm: float | None


class WorkoutOut(BaseModel):
    id: int
    day: date
    started_at: datetime
    finished_at: datetime | None
    sets: list[SetOut]


class FinishedWorkout(BaseModel):
    workout: WorkoutOut
    xp_awarded: int
    active_minutes: float
    hard_sets: int


class WorkoutSummary(BaseModel):
    id: int
    day: date
    started_at: datetime
    finished_at: datetime | None
    sets: int
    volume_kg: float
    xp: int


class SetPatch(BaseModel):
    """Partial edit of a logged set; omitted fields keep their value."""

    weight_kg: float | None = Field(default=None, ge=0, le=500)
    reps: int | None = Field(default=None, ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)
