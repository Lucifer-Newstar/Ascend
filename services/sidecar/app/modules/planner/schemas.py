from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import StrictIn

Focus = Literal["strength", "muscle", "fat_loss", "skills", "general"]
Experience = Literal["beginner", "intermediate", "advanced"]
EquipmentChoice = Literal["none", "pullup_bar", "rings", "dumbbells", "bench", "gym"]
Diet = Literal["veg", "egg", "nonveg"]
Section = Literal["gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation"]
Phrased = Literal["rules", "ollama"]


class FlagOut(BaseModel):
    code: str
    severity: Literal["info", "warn", "block"]
    message: str
    numbers: dict[str, float] = {}


class GoalCheckIn(StrictIn):
    """Any subset of a goal; each part present is checked (goalcheck-v1)."""

    weight_kg: float | None = Field(default=None, ge=30, le=300)
    target_weight_kg: float | None = Field(default=None, ge=30, le=300)
    weeks: float | None = Field(default=None, gt=0, le=520)
    kcal: float | None = Field(default=None, ge=0, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=600)
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    minutes: int | None = Field(default=None, ge=5, le=300)
    experience: Experience | None = None
    lift_current_kg: float | None = Field(default=None, gt=0, le=600)
    lift_target_kg: float | None = Field(default=None, gt=0, le=600)
    lift_weeks: float | None = Field(default=None, gt=0, le=520)
    age: int | None = Field(default=None, ge=13, le=100)
    # v1.2: with the height, a gain from an underweight start is judged as a catch-up gain.
    height_cm: float | None = Field(default=None, ge=100, le=250)


class GoalCheckOut(BaseModel):
    flags: list[FlagOut]
    worst: Literal["info", "warn", "block"] | None
    algo_version: str


class WorkoutPlanIn(StrictIn):
    focus: Focus = "general"
    experience: Experience | None = None  # default: the profile's, else beginner
    days_per_week: int = Field(default=3, ge=1, le=7)
    minutes: int = Field(default=60, ge=10, le=180)
    equipment: list[EquipmentChoice] | None = None  # default: the profile's checklist
    use_ai: bool = True
    # v1.2: generate for one section. gym/calisthenics use the split rules (calisthenics
    # leaves gym kit out); cardio, martial arts, flexibility and meditation use section_gen.
    section: Section | None = None


class SlotIO(BaseModel):
    exercise: str = Field(min_length=1, max_length=120)
    sets: int = Field(ge=1, le=10)
    rep_low: int = Field(ge=1, le=100)
    rep_high: int = Field(ge=1, le=100)
    target_rpe: float = Field(default=8.0, ge=5, le=10)
    rest_s: int = Field(default=120, ge=0, le=900)
    exercise_id: int | None = None


class DayIO(BaseModel):
    key: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=60)
    focus: str = Field(default="", max_length=80)
    weekday: int = Field(ge=0, le=6)
    slots: list[SlotIO] = Field(min_length=1, max_length=12)


class ProgramDraft(StrictIn):
    name: str = Field(min_length=1, max_length=80)
    summary: str = Field(default="", max_length=400)
    level: Experience = "beginner"
    equipment: Literal["gym", "dumbbells", "bodyweight"] = "gym"
    days: list[DayIO] = Field(min_length=1, max_length=7)
    notes: list[str] = Field(default_factory=list, max_length=10)


class WorkoutPlanOut(BaseModel):
    draft: ProgramDraft
    flags: list[FlagOut]
    phrased_by: Phrased
    algo_version: str


class CustomProgramOut(ProgramDraft):
    id: int
    key: str
    algo_version: str
    created_at: datetime
    updated_at: datetime
    following: bool = False


class DietPlanIn(StrictIn):
    diet: Diet = "nonveg"
    kcal_target: int | None = Field(default=None, ge=800, le=6000)  # default: the engine's
    use_ai: bool = True


class PlanFoodItemOut(BaseModel):
    food: str
    portions: float
    portion_label: str
    kcal: int
    protein_g: float


class PlanMealOut(BaseModel):
    meal: str
    items: list[PlanFoodItemOut]
    kcal: int
    protein_g: float


class DayPlanOut(BaseModel):
    day: int
    meals: list[PlanMealOut]
    kcal: int
    protein_g: float


class DietPlanOut(BaseModel):
    kcal_target: int
    protein_target_g: int
    diet: Diet
    days: list[DayPlanOut]
    notes: list[str]
    flags: list[FlagOut]
    phrased_by: Phrased
    algo_version: str


class DietSaveIn(StrictIn):
    name: str = Field(default="My meal plan", min_length=1, max_length=80)
    plan: DietPlanOut


class SavedDietOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    active: bool
    plan: DietPlanOut
