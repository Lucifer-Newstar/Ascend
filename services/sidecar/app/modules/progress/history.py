"""History (workouts + meals grouped by day) and JSON/CSV export."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.modules.gamification.models import QuestItem, XpEvent
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.models import Meal
from app.modules.nutrition.schemas import MealOut
from app.modules.progress import service as progress
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Workout
from app.modules.workouts.schemas import WorkoutOut

EXPORT_SCHEMA_VERSION = 1


class HistoryDay(BaseModel):
    day: date
    workouts: list[WorkoutOut]
    meals: list[MealOut]
    kcal_in: float
    sets: int
    xp: int


def history(db: Session, now: datetime, days: int = 30) -> list[HistoryDay]:
    since = now.date() - timedelta(days=days - 1)
    ws = db.scalars(select(Workout).where(Workout.day >= since).order_by(Workout.started_at)).all()
    ms = db.scalars(select(Meal).where(Meal.day >= since).order_by(Meal.logged_at)).all()
    xs = db.scalars(select(XpEvent).where(XpEvent.day >= since)).all()
    by_day: dict[date, HistoryDay] = {}

    def bucket(d: date) -> HistoryDay:
        if d not in by_day:
            by_day[d] = HistoryDay(day=d, workouts=[], meals=[], kcal_in=0, sets=0, xp=0)
        return by_day[d]

    for w in ws:
        h = bucket(w.day)
        h.workouts.append(workouts.workout_out(w))
        h.sets += len(w.sets)
    for m in ms:
        h = bucket(m.day)
        out = nutrition.meal_out(m)
        h.meals.append(out)
        h.kcal_in = round(h.kcal_in + out.kcal, 1)
    for x in xs:
        bucket(x.day).xp += x.amount
    return [by_day[d] for d in sorted(by_day, reverse=True)]


def export_json(db: Session, now: datetime) -> dict[str, Any]:
    profile = progress.get_profile(db)
    ws = db.scalars(select(Workout).order_by(Workout.started_at)).all()
    ms = db.scalars(select(Meal).order_by(Meal.logged_at)).all()
    return {
        "app": "ASCEND",
        "app_version": __version__,
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": now.isoformat(),
        "profile": None if profile is None else {
            k: getattr(profile, k)
            for k in ("name", "age", "sex", "height_cm", "weight_kg", "goal", "activity")
        },
        "workouts": [workouts.workout_out(w).model_dump(mode="json") for w in ws],
        "meals": [nutrition.meal_out(m).model_dump(mode="json") for m in ms],
        "xp_events": [
            {"day": x.day.isoformat(), "source": x.source, "amount": x.amount,
             "formula_version": x.formula_version, "note": x.note}
            for x in db.scalars(select(XpEvent).order_by(XpEvent.id)).all()
        ],
        "quests": [
            {"day": q.day.isoformat(), "title": q.title, "xp": q.xp,
             "completed": q.completed_at is not None}
            for q in db.scalars(select(QuestItem).order_by(QuestItem.id)).all()
        ],
    }


# Column order follows Strong's CSV export where it overlaps, so other tools can read it.
WORKOUT_CSV_COLUMNS = ["Date", "Workout #", "Exercise Name", "Set Order", "Weight (kg)",
                       "Reps", "RPE", "e1RM (kg)", "PR"]
MEAL_CSV_COLUMNS = ["Date", "Meal", "Food", "Portions", "kcal", "Protein (g)", "Carbs (g)",
                    "Fat (g)"]


def export_csv(db: Session, kind: str) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    if kind == "workouts":
        writer.writerow(WORKOUT_CSV_COLUMNS)
        for w in db.scalars(select(Workout).order_by(Workout.started_at)).all():
            order: dict[int, int] = {}
            for s in w.sets:
                order[s.exercise_id] = order.get(s.exercise_id, 0) + 1
                writer.writerow([s.performed_at.isoformat(sep=" "), w.id, s.exercise.name,
                                 order[s.exercise_id], s.weight_kg, s.reps,
                                 "" if s.rpe is None else s.rpe,
                                 "" if s.e1rm is None else s.e1rm, int(s.is_pr)])
    elif kind == "meals":
        writer.writerow(MEAL_CSV_COLUMNS)
        for m in db.scalars(select(Meal).order_by(Meal.logged_at)).all():
            for i in m.items:
                writer.writerow([m.logged_at.isoformat(sep=" "), m.meal_type, i.food_name,
                                 i.portions, i.kcal, i.protein_g, i.carbs_g, i.fat_g])
    else:
        raise ValueError(f"unknown export kind {kind!r}")
    return buf.getvalue()
