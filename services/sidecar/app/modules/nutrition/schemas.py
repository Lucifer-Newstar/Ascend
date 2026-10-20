from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class MealItemIn(BaseModel):
    food_id: int
    portions: float = Field(gt=0, le=20)


class MealIn(BaseModel):
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
    protein_target_g: int | None
    values_are_approximate: bool = True


class MealLoggedOut(BaseModel):
    meal: MealOut
    xp_awarded: int
