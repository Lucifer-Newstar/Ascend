from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileIn(BaseModel):
    name: str = Field(default="", max_length=80)
    age: int = Field(ge=13, le=100)
    sex: Literal["male", "female"]
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    goal: Literal["cut", "maintain", "bulk"]
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    target_weight_kg: float | None = Field(default=None, ge=30, le=300)


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


class SettingsIn(BaseModel):
    """Partial update: only the fields sent are changed."""

    ai_enabled: bool | None = None
    units: Units | None = None
    theme: Theme | None = None
    sessions_per_week: int | None = Field(default=None, ge=1, le=7)


class BodyMetricIn(BaseModel):
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


class MeasurementIn(BaseModel):
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


class CheckinIn(BaseModel):
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
