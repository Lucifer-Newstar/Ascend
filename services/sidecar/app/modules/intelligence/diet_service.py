"""Database side of tdee-v1 and insights-v1: reads daily intake, protein and weigh-ins
and hands plain values to the pure engines (ADR-0018, ADR-0019)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.intelligence import insights as ins
from app.modules.intelligence import tdee as td
from app.modules.nutrition.models import Meal, MealItem
from app.modules.progress import service as progress
from app.modules.progress.models import BodyMetric

HISTORY_DAYS = 365


def profile_input(db: Session) -> td.Profile | None:
    p = progress.get_profile(db)
    if p is None:
        return None
    return td.Profile(
        sex=p.sex,
        age=p.age,
        height_cm=p.height_cm,
        weight_kg=p.weight_kg,
        activity=p.activity,
        goal=p.goal,
    )


def nutrition_days(db: Session, today: date, days: int = HISTORY_DAYS) -> list[ins.NutritionDay]:
    since = today - timedelta(days=days - 1)
    rows = db.execute(
        select(Meal.day, func.sum(MealItem.kcal), func.sum(MealItem.protein_g))
        .join(MealItem, MealItem.meal_id == Meal.id)
        .where(Meal.day >= since, Meal.day <= today)
        .group_by(Meal.day)
    ).all()
    return [ins.NutritionDay(d, float(k or 0), float(p or 0)) for d, k, p in rows]


def weigh_ins(db: Session, today: date, days: int = HISTORY_DAYS) -> dict[date, float]:
    since = datetime.combine(today - timedelta(days=days - 1), time.min)
    until = datetime.combine(today, time.max)
    per_day: dict[date, list[float]] = {}
    for at, kg in db.execute(
        select(BodyMetric.measured_at, BodyMetric.weight_kg).where(
            BodyMetric.measured_at >= since, BodyMetric.measured_at <= until
        )
    ).all():
        per_day.setdefault(at.date(), []).append(float(kg))
    return {d: sum(v) / len(v) for d, v in per_day.items()}


def day_inputs(db: Session, today: date) -> tuple[list[td.DayInput], list[ins.NutritionDay]]:
    food = nutrition_days(db, today)
    weights = weigh_ins(db, today)
    intake = {n.day: n.kcal for n in food}
    days = sorted(set(intake) | set(weights))
    return [td.DayInput(d, weights.get(d), intake.get(d)) for d in days], food


def tdee_report(db: Session, today: date) -> td.TdeeResult | None:
    profile = profile_input(db)
    if profile is None:
        return None
    days, _ = day_inputs(db, today)
    return td.compute(days, profile, today)


def calorie_target(db: Session, today: date) -> tuple[int, str] | None:
    """The day's calorie target: this week's adaptive target once tdee-v1 has set one,
    else the Mifflin-St Jeor target. ``None`` without a profile."""
    report = tdee_report(db, today)
    if report is None:
        return None
    if report.target_source == "adaptive":
        return report.target_kcal, "adaptive"
    return report.formula_target_kcal, "formula"


def insight_report(db: Session, today: date) -> tuple[ins.InsightReport, td.TdeeResult] | None:
    """Findings for the 7 complete days before ``today``."""
    profile = profile_input(db)
    p = progress.get_profile(db)
    if profile is None or p is None:
        return None
    days, food = day_inputs(db, today)
    report = td.compute(days, profile, today)
    target = (
        report.target_kcal if report.target_source == "adaptive" else report.formula_target_kcal
    )
    protein = progress.energy_for(p).protein_target_g
    end = today - timedelta(days=1)
    return ins.weekly(food, report, profile.goal, target, protein, end), report
