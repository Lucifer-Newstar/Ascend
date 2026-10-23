from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import StrictIn

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    portion_label: str
    portion_g: float
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    source: str


class FoodIn(StrictIn):
    """A food the user adds themselves; nutrients are per ONE portion."""

    name: str = Field(min_length=1, max_length=80)
    portion_label: str = Field(default="1 portion", min_length=1, max_length=30)
    portion_g: float = Field(default=100, gt=0, le=2000)
    kcal: float = Field(ge=0, le=3000)
    protein_g: float = Field(default=0, ge=0, le=300)
    carbs_g: float = Field(default=0, ge=0, le=500)
    fat_g: float = Field(default=0, ge=0, le=300)


class MealItemIn(StrictIn):
    food_id: int
    portions: float = Field(gt=0, le=20)


class MealIn(StrictIn):
    meal_type: MealType
    items: list[MealItemIn] = Field(min_length=1, max_length=30)


class MealItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    food_id: int
    food_name: str
    portions: float
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day: date
    meal_type: str
    logged_at: datetime
    items: list[MealItemOut]
    kcal: float


class Totals(BaseModel):
    kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0


class DayLog(BaseModel):
    day: date
    meals: list[MealOut]
    totals: Totals
    kcal_target: int | None
    #: "adaptive" once tdee-v1 has set this week's target (ADR-0018), else "formula".
    kcal_target_source: Literal["formula", "adaptive"] | None = None
    protein_target_g: int | None
    values_are_approximate: bool = True


class MealLoggedOut(BaseModel):
    meal: MealOut
    xp_awarded: int


class FoodGuideline(BaseModel):
    title: str
    detail: str


class FoodGroupCount(BaseModel):
    key: str
    label: str
    count: int
    core: bool


class FoodGuideOut(BaseModel):
    """v1.2 food rules: India's food guidelines (ICMR-NIN 2024) and a rough check of one
    day's logged meals against them. Guidance only; it never changes your targets."""

    day: date
    source: str
    version: str
    guidelines: list[FoodGuideline]
    foods_logged: int
    groups: list[FoodGroupCount]
    missing: list[str]
    hfss: list[str]
    tips: list[str]
