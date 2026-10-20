from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import StrictIn


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
    slug: str | None = None
    # reps | hold (seconds per set) | time (cardio, stretching, meditation)
    measure: str = "reps"
    difficulty: str | None = None
    pattern: str = "other"
    image: str | None = None
    # ascend | free-exercise-db | custom
    source: str = "ascend"
    is_custom: bool = False
    aliases: list[str] = []


class SkillLinkOut(BaseModel):
    skill_key: str
    skill_name: str
    step_name: str | None = None
    # "step": the exercise is a step of the tree; "feeder": it builds strength for it
    role: str


class AttributionOut(BaseModel):
    source: str
    title: str
    url: str
    license: str


class ExerciseDetail(ExerciseOut):
    instructions: list[str] = []
    mechanic: str | None = None
    rep_low: int | None = None
    rep_high: int | None = None
    # field -> library | rules | local_ai | wger | wikipedia | user
    field_sources: dict[str, str] = {}
    attribution: list[AttributionOut] = []
    source_ref: str | None = None
    created_at: datetime | None = None
    skills: list[SkillLinkOut] = []
    sets_logged: int = 0


class SetIn(StrictIn):
    """One set. Lifts send weight + reps; time-based sections send duration_s
    (and distance_m for cardio). The service checks the right fields are present."""

    exercise_id: int
    weight_kg: float = Field(default=0, ge=0, le=500)
    reps: int = Field(default=1, ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)
    duration_s: int | None = Field(default=None, ge=1, le=6 * 3600)
    distance_m: float | None = Field(default=None, ge=0, le=300_000)
    avg_hr: int | None = Field(default=None, ge=30, le=230)


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    exercise_name: str
    weight_kg: float
    reps: int
    rpe: float | None
    duration_s: int | None = None
    distance_m: float | None = None
    avg_hr: int | None = None
    e1rm: float | None
    is_pr: bool
    performed_at: datetime
    # The exercise's measure, so a client can show "45 s hold" without a lookup.
    measure: str = "reps"


class LoggedSet(BaseModel):
    set: SetOut
    xp_awarded: int
    previous_best_e1rm: float | None


class WorkoutOut(BaseModel):
    id: int
    day: date
    section: str = "gym"
    started_at: datetime
    finished_at: datetime | None
    sets: list[SetOut]
    source: str = "app"
    title: str = ""


class FinishedWorkout(BaseModel):
    workout: WorkoutOut
    xp_awarded: int
    active_minutes: float
    hard_sets: int


class WorkoutSummary(BaseModel):
    id: int
    day: date
    section: str = "gym"
    started_at: datetime
    finished_at: datetime | None
    sets: int
    volume_kg: float
    xp: int
    # "app", or the app an imported session came from ("strong", "hevy").
    source: str = "app"
    title: str = ""


class SetPatch(StrictIn):
    """Partial edit of a logged set; omitted fields keep their value."""

    weight_kg: float | None = Field(default=None, ge=0, le=500)
    reps: int | None = Field(default=None, ge=1, le=100)
    rpe: float | None = Field(default=None, ge=1, le=10)
    duration_s: int | None = Field(default=None, ge=1, le=6 * 3600)
    distance_m: float | None = Field(default=None, ge=0, le=300_000)


class PROut(BaseModel):
    exercise_id: int
    exercise: str
    type: str = "e1rm"
    value: float
    weight_kg: float
    reps: int
    formula: str = "epley"
    algo_version: str
    achieved_at: datetime
    set_id: int
