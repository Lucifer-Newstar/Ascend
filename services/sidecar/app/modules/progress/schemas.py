from __future__ import annotations

from datetime import datetime
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


class SettingsOut(BaseModel):
    ai_enabled: bool


class SettingsIn(BaseModel):
    ai_enabled: bool
