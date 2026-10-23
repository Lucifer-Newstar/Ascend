"""Energy targets: Mifflin-St Jeor BMR x activity factor.

Every number here is an ESTIMATE. Mifflin-St Jeor is a standard population
equation; individual expenditure can differ by several hundred kcal. The UI
labels these values as estimates.
"""

from __future__ import annotations

from typing import Literal

FORMULA_VERSION = "tdee-msj-v1"

Sex = Literal["male", "female"]
Goal = Literal["cut", "maintain", "bulk"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]

ACTIVITY_FACTORS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# kcal/day adjustment applied on top of TDEE for each goal
GOAL_ADJUSTMENT: dict[str, int] = {"cut": -500, "maintain": 0, "bulk": 300}


def bmr_mifflin_st_jeor(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """BMR (kcal/day) = 10 W + 6.25 H - 5 A + s, with s = +5 (male) / -161 (female)."""
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        raise ValueError("weight, height and age must be positive")
    s = 5 if sex == "male" else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def tdee(bmr: float, activity: Activity) -> float:
    return bmr * ACTIVITY_FACTORS[activity]


# The planner's own safety lines (planner/validate.py): no deficit for a growing body and
# none below a healthy BMI. The daily target follows them too.
ADULT_AGE = 18
MIN_BMI_FOR_DEFICIT = 18.5


def energy_goal(goal: str, weight_kg: float, height_cm: float, age: int) -> str:
    """The goal the calorie target is worked out for: "cut" counts as "maintain" under 18
    or below a BMI of 18.5, so a "lose fat" choice never sets a deficit there."""
    if goal != "cut":
        return goal
    if age < ADULT_AGE:
        return "maintain"
    if height_cm > 0 and weight_kg / (height_cm / 100) ** 2 < MIN_BMI_FOR_DEFICIT:
        return "maintain"
    return goal


def calorie_target(tdee_kcal: float, goal: Goal) -> int:
    # Never recommend below 1200 kcal: a safety floor, not a target.
    return max(1200, round(tdee_kcal + GOAL_ADJUSTMENT[goal]))


def protein_target_g(weight_kg: float, goal: Goal) -> int:
    # 1.6 g/kg (cut/bulk) or 1.4 g/kg (maintain): common sports-nutrition range, estimate.
    per_kg = 1.4 if goal == "maintain" else 1.6
    return round(weight_kg * per_kg)
