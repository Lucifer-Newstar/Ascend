"""History (workouts + meals grouped by day) and JSON/CSV export."""

from __future__ import annotations

import csv
import io
import json
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
from app.modules.progress.models import BodyMetric, Checkin, Measurement, Setting
from app.modules.skills.models import SkillUnlock
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise, Workout
from app.modules.workouts.schemas import WorkoutOut

# 2: adds body metrics, tape measurements, check-ins, skill unlocks, custom exercises,
#    settings, and the profile's target weight, focus, equipment and baseline.
EXPORT_SCHEMA_VERSION = 2


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


def _loads(text: str | None, default: Any) -> Any:
    try:
        return json.loads(text) if text else default
    except ValueError:
        return default


def _profile(db: Session) -> dict[str, Any] | None:
    p = progress.get_profile(db)
    if p is None:
        return None
    out: dict[str, Any] = {
        k: getattr(p, k)
        for k in (
            "name",
            "age",
            "sex",
            "height_cm",
            "weight_kg",
            "target_weight_kg",
            "goal",
            "activity",
            "focus",
        )
    }
    out["equipment"] = _loads(p.equipment_json, [])
    out["baseline"] = _loads(p.baseline_json, {})
    return out


def export_json(db: Session, now: datetime) -> dict[str, Any]:
    """Everything the user entered, as one JSON document ("export everything")."""
    ws = db.scalars(select(Workout).order_by(Workout.started_at)).all()
    ms = db.scalars(select(Meal).order_by(Meal.logged_at)).all()
    return {
        "app": "ASCEND",
        "app_version": __version__,
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": now.isoformat(),
        "profile": _profile(db),
        "settings": {s.key: s.value for s in db.scalars(select(Setting).order_by(Setting.key))},
        "body_metrics": [
            {
                "measured_at": b.measured_at.isoformat(),
                "weight_kg": b.weight_kg,
                "waist_cm": b.waist_cm,
                "resting_hr": b.resting_hr,
            }
            for b in db.scalars(select(BodyMetric).order_by(BodyMetric.measured_at))
        ],
        "measurements": [
            {"measured_at": m.measured_at.isoformat(), "site": m.site, "cm": m.cm}
            for m in db.scalars(select(Measurement).order_by(Measurement.measured_at))
        ],
        "checkins": [
            {
                "day": c.day.isoformat(),
                "sleep": c.sleep,
                "energy": c.energy,
                "soreness": c.soreness,
                "mood": c.mood,
                "readiness": c.readiness,
                "band": c.band,
                "algo_version": c.algo_version,
                "quest_note": c.quest_note,
            }
            for c in db.scalars(select(Checkin).order_by(Checkin.day))
        ],
        "custom_exercises": [
            {**workouts.exercise_out(e).model_dump(mode="json"), "archived": e.archived}
            for e in db.scalars(
                select(Exercise).where(Exercise.is_custom.is_(True)).order_by(Exercise.id)
            )
        ],
        "workouts": [workouts.workout_out(w).model_dump(mode="json") for w in ws],
        "meals": [nutrition.meal_out(m).model_dump(mode="json") for m in ms],
        "skill_unlocks": [
            {
                "skill": u.skill_key,
                "step": u.step_key,
                "unlocked_at": u.unlocked_at.isoformat(),
                "source": u.source,
            }
            for u in db.scalars(select(SkillUnlock).order_by(SkillUnlock.id))
        ],
        "xp_events": [
            {
                "day": x.day.isoformat(),
                "source": x.source,
                "amount": x.amount,
                "formula_version": x.formula_version,
                "note": x.note,
            }
            for x in db.scalars(select(XpEvent).order_by(XpEvent.id)).all()
        ],
        "quests": [
            {
                "day": q.day.isoformat(),
                "title": q.title,
                "xp": q.xp,
                "completed": q.completed_at is not None,
            }
            for q in db.scalars(select(QuestItem).order_by(QuestItem.id)).all()
        ],
    }


# Strong's classic CSV layout (comma separated), so ASCEND's own importer, Strong-
# compatible tools and spreadsheets can all read it, plus ASCEND's extra columns. "Date"
# is the workout's start, as in Strong; the importer groups sets by it.
WORKOUT_CSV_COLUMNS = [
    "Date",
    "Workout Name",
    "Workout #",
    "Exercise Name",
    "Set Order",
    "Weight",
    "Weight Unit",
    "Reps",
    "RPE",
    "Distance",
    "Distance Unit",
    "Seconds",
    "Avg HR",
    "e1RM (kg)",
    "PR",
    "Workout Duration",
]
MEAL_CSV_COLUMNS = [
    "Date",
    "Meal",
    "Food",
    "Portions",
    "kcal",
    "Protein (g)",
    "Carbs (g)",
    "Fat (g)",
]

# A cell starting with one of these is a formula to Excel/LibreOffice ("=HYPERLINK(...)").
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def csv_text(value: str) -> str:
    """A user-typed text cell, defused for spreadsheets: a leading formula character gets
    a "'" in front (the importer strips it again)."""
    return f"'{value}" if value.startswith(_FORMULA_START) else value


def _blank(value: object) -> object:
    return "" if value is None else value


def _stamp(at: datetime) -> str:
    return at.strftime("%Y-%m-%d %H:%M:%S")


def export_csv(db: Session, kind: str) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    if kind == "workouts":
        writer.writerow(WORKOUT_CSV_COLUMNS)
        for w in db.scalars(select(Workout).order_by(Workout.started_at)).all():
            title = (
                w.notes if w.source != "app" and w.notes else w.section.replace("_", " ").title()
            )
            seconds = (
                int((w.finished_at - w.started_at).total_seconds())
                if w.finished_at is not None and w.finished_at >= w.started_at
                else None
            )
            order: dict[int, int] = {}
            for s in w.sets:
                order[s.exercise_id] = order.get(s.exercise_id, 0) + 1
                writer.writerow(
                    [
                        _stamp(w.started_at),
                        csv_text(title),
                        w.id,
                        csv_text(s.exercise.name),
                        order[s.exercise_id],
                        s.weight_kg,
                        "kg",
                        s.reps,
                        _blank(s.rpe),
                        "" if s.distance_m is None else round(s.distance_m / 1000, 4),
                        "km",
                        _blank(s.duration_s),
                        _blank(s.avg_hr),
                        _blank(s.e1rm),
                        int(s.is_pr),
                        _blank(seconds),
                    ]
                )
    elif kind == "meals":
        writer.writerow(MEAL_CSV_COLUMNS)
        for m in db.scalars(select(Meal).order_by(Meal.logged_at)).all():
            for i in m.items:
                writer.writerow(
                    [
                        _stamp(m.logged_at),
                        csv_text(m.meal_type),
                        csv_text(i.food_name),
                        i.portions,
                        i.kcal,
                        i.protein_g,
                        i.carbs_g,
                        i.fat_g,
                    ]
                )
    else:
        raise ValueError(f"unknown export kind {kind!r}")
    return buf.getvalue()
