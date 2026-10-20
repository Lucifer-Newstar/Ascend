from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import StrictIn


class ProfileIn(BaseModel):
    # PUT /profile is a whole-object update and clients echo back what GET returned,
    # so read-only fields such as `energy` are ignored rather than rejected.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(default="", max_length=80)
    age: int = Field(ge=13, le=100)
    sex: Literal["male", "female"]
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    goal: Literal["cut", "maintain", "bulk"]
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    target_weight_kg: float | None = Field(default=None, ge=30, le=300)
    # Onboarding answers. Equipment: an empty list means "not stated" (nothing filtered).
    focus: Literal["strength", "muscle", "skills", "fat_loss"] | None = None
    equipment: list[Literal["none", "pullup_bar", "rings", "dumbbells", "gym"]] = Field(
        default_factory=list, max_length=5
    )


class BaselineIn(StrictIn):
    """The Awakening baseline test. Zero or null means "not done"; at least one result."""

    pushups: int | None = Field(default=None, ge=0, le=200)
    pullups: int | None = Field(default=None, ge=0, le=60)
    dead_hang_s: int | None = Field(default=None, ge=0, le=600)
    plank_s: int | None = Field(default=None, ge=0, le=1800)
    squats_60s: int | None = Field(default=None, ge=0, le=120)
    bodyweight_kg: float | None = Field(default=None, ge=30, le=300)


class BaselineResult(BaseModel):
    pushups: int | None = None
    pullups: int | None = None
    dead_hang_s: int | None = None
    plank_s: int | None = None
    squats_60s: int | None = None
    bodyweight_kg: float | None = None
    taken_at: datetime


class BaselineOut(BaseModel):
    baseline: BaselineResult
    workout_id: int
    sets_logged: int
    xp_awarded: int
    level: int
    rank: str
    # Skill-tree steps the baseline sets unlocked ("Skill: Step"); often none, since most
    # steps need two sessions.
    steps_unlocked: list[str]


class EnergyTargets(BaseModel):
    bmr: int
    tdee: int
    kcal_target: int
    protein_target_g: int
    formula_version: str
    is_estimate: bool = True


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    energy: EnergyTargets
    baseline: BaselineResult | None = None


class MuscleStateOut(BaseModel):
    key: str
    label: str
    group: str
    map_slug: str
    status: Literal["under", "optimal", "recovering", "over", "no_data"]
    es_7d: float
    weekly_low: float
    weekly_high: float
    readiness: float
    ready_at: datetime | None


Units = Literal["metric", "imperial"]
Theme = Literal["dark", "light", "system"]


class SettingsOut(BaseModel):
    ai_enabled: bool
    units: Units = "metric"
    theme: Theme = "dark"
    sessions_per_week: int = 3
    reduce_motion: bool = False
    # Off by default: when on, "Add your own exercise" may ask wger.de (the only
    # feature that contacts the internet, and only when the user asks per exercise).
    online_lookup: bool = False


class SettingsIn(StrictIn):
    """Partial update: only the fields sent are changed."""

    ai_enabled: bool | None = None
    units: Units | None = None
    theme: Theme | None = None
    sessions_per_week: int | None = Field(default=None, ge=1, le=7)
    reduce_motion: bool | None = None
    online_lookup: bool | None = None


class BodyMetricIn(StrictIn):
    measured_at: datetime | None = None
    weight_kg: float = Field(ge=20, le=300)
    waist_cm: float | None = Field(default=None, ge=30, le=250)
    resting_hr: int | None = Field(default=None, ge=25, le=150)


class BodyMetricOut(BaseModel):
    id: int
    measured_at: datetime
    weight_kg: float
    trend_kg: float
    waist_cm: float | None
    resting_hr: int | None


MeasurementSite = Literal["waist", "hips", "chest", "arm", "thigh", "calf", "neck"]


class MeasurementIn(StrictIn):
    measured_at: datetime | None = None
    site: MeasurementSite
    cm: float = Field(ge=10, le=250)


class MeasurementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    measured_at: datetime
    site: str
    cm: float
    change_cm: float | None = None


class EtaOut(BaseModel):
    goal_kg: float | None
    current_trend_kg: float | None
    rate_kg_per_week: float | None
    eta_from: date | None
    eta_to: date | None
    confidence: Literal["low", "medium", "high"]
    on_track: bool
    reason: str | None
    formula_version: str
    note: Literal["Estimate, not a promise"] = "Estimate, not a promise"


class CheckinIn(StrictIn):
    sleep: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    soreness: Literal["none", "some", "a_lot"]
    mood: int = Field(ge=1, le=5)


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    day: date
    sleep: int
    energy: int
    soreness: str
    mood: int
    readiness: int
    band: Literal["green", "amber", "red"]
    quest_adjustment: str
    algo_version: str
