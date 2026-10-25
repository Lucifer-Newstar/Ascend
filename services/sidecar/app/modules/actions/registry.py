"""actions-v1: the fixed allowlist of in-app actions.

Each action is a typed parameter model plus three functions over existing services:
describe (what will change, shown on the confirm card), execute and, where possible, undo.
No action runs SQL, touches files or the network directly; they call the same services the
pages use. Nothing executes without a confirm call; destructive actions also need a word
typed by the user.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus
from app.modules.actions import resolve
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.models import Food
from app.modules.nutrition.schemas import FoodIn, MealIn, MealItemIn
from app.modules.progress import body
from app.modules.progress.schemas import BodyMetricIn
from app.modules.workouts import programs_service
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise
from app.modules.workouts.schemas import SetIn

ACTIONS_VERSION = "actions-v2"
Risk = Literal["low", "normal", "destructive"]


class ActionError(Exception):
    """A proposal that can't run (unknown exercise, food or program...)."""


# --- parameter models -----------------------------------------------------------------


class SetItemP(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    reps: int = Field(ge=1, le=100)
    weight_kg: float = Field(default=0, ge=0, le=500)
    sets: int = Field(default=1, ge=1, le=10)


class LogSetP(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    reps: int = Field(ge=1, le=100)
    weight_kg: float = Field(default=0, ge=0, le=500)
    sets: int = Field(default=1, ge=1, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)
    # v1.3: "10 pushups and 10 squats" is one card; the first item is the fields above.
    more: list[SetItemP] = Field(default_factory=list, max_length=7)


class LogHoldP(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    seconds: int = Field(ge=1, le=3600)
    sets: int = Field(default=1, ge=1, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)


class LogWeightP(BaseModel):
    weight_kg: float = Field(ge=20, le=300)


class MealItemP(BaseModel):
    food: str = Field(min_length=1, max_length=80)
    portions: float = Field(default=1, gt=0, le=20)


class LogMealP(BaseModel):
    food: str = Field(min_length=1, max_length=80)
    portions: float = Field(default=1, gt=0, le=20)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = "snack"
    # v1.3: "2 idli and sambar" is one meal with several items; the first is food/portions.
    more: list[MealItemP] = Field(default_factory=list, max_length=7)

    def items(self) -> list[MealItemP]:
        return [MealItemP(food=self.food, portions=self.portions), *self.more]


class AddFoodP(BaseModel):
    """v1.3: a food of the user's own, added from the chat ("add food ...")."""

    name: str = Field(min_length=1, max_length=80)
    portion_label: str = Field(default="1 serving", min_length=1, max_length=30)
    portion_g: float = Field(default=100, gt=0, le=2000)
    kcal: float = Field(ge=0, le=5000)
    protein_g: float = Field(default=0, ge=0, le=500)
    carbs_g: float = Field(default=0, ge=0, le=1000)
    fat_g: float = Field(default=0, ge=0, le=500)


class FollowProgramP(BaseModel):
    program: str = Field(min_length=1, max_length=80)


class EraseDataP(BaseModel):
    keep_preferences: bool = True


# --- name resolution ------------------------------------------------------------------

PROGRAM_ALIASES = {
    "ppl": "ppl_6",
    "push pull legs": "ppl_6",
    "push/pull/legs": "ppl_6",
    "upper lower": "upper_lower_4",
    "upper/lower": "upper_lower_4",
    "full body": "full_body_3",
    "home": "home_full_body_3",
    "home full body": "home_full_body_3",
    "bodyweight starter": "bodyweight_starter_3",
    "starter": "bodyweight_starter_3",
    "beginner": "bodyweight_starter_3",
    "beginners": "bodyweight_starter_3",
    "bar starter": "bar_floor_starter_3",
    "bar and floor": "bar_floor_starter_3",
    "4 day split": "upper_lower_4",
    "3 day split": "full_body_3",
    "6 day split": "ppl_6",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def resolve_exercise(db: Session, query: str, strict: bool = False) -> Exercise:
    """An exercise by name, plural, alias, typo or (unless `strict`) a name holding the
    words. v1.3: the user's equipment decides between candidates ("squats" with no barbell
    is the bodyweight squat, "bench" with only dumbbells is the dumbbell bench press). A
    log records what was done, so the bench rule of the planner does not apply here."""
    from app.modules.workouts.equipment import allowed_for_profile, fits

    allowed = allowed_for_profile(db)
    rows = list(db.scalars(select(Exercise).where(Exercise.archived.is_(False))))
    try:
        return resolve.pick_exercise(query, rows, lambda e: fits(e.equipment, allowed), strict)
    except resolve.NotFoundError:
        raise ActionError(f"I couldn't find an exercise called \u201c{query}\u201d.") from None


def resolve_food(db: Session, query: str) -> tuple[int, str]:
    """One food for a name (an alias for several foods counts as its first)."""
    foods = resolve_foods(db, query)
    return foods[0].id, foods[0].name


def resolve_foods(db: Session, query: str, grams: bool = False) -> list[Food]:
    try:
        return resolve.resolve_foods(db, query, grams)
    except resolve.AmbiguousError as e:
        raise AmbiguousName(e.query, e.options) from None
    except resolve.NotFoundError:
        raise UnknownFood(query) from None


class AmbiguousName(ActionError):
    def __init__(self, query: str, options: list[str]) -> None:
        self.query = query
        self.options = options
        super().__init__(str(resolve.AmbiguousError(query, options)))


class UnknownFood(ActionError):
    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(
            f"\u201c{query}\u201d isn't in the food table yet. You can add it as your own food "
            "(Fuel > Add your own food, or tell me: add food <name> <kcal> kcal)."
        )


def resolve_program(db: Session, query: str) -> tuple[str, str]:
    q = _norm(query)
    key = PROGRAM_ALIASES.get(q)
    catalog = programs_service.catalog(db)
    for p in catalog:
        if p.key == key or _norm(p.name) == q:
            return p.key, p.name
    for p in catalog:  # a word of the name ("mobility"), never a stray letter or number
        if len(q) >= 3 and not q[0].isdigit() and re.search(rf"\b{re.escape(q)}\b", _norm(p.name)):
            return p.key, p.name
    from app.modules.planner import service as planner

    for c in planner.list_programs(db):
        if _norm(c.name) == q or (len(q) >= 3 and q in _norm(c.name)):
            return c.key, c.name
    raise ActionError(f"I don't know a program called \u201c{query}\u201d.")


def _kg(x: float) -> str:
    return f"{x:g} kg"


# --- the allowlist --------------------------------------------------------------------

Describe = Callable[[Session, Any], list[str]]
Execute = Callable[[Session, EventBus, datetime, Any], tuple[dict[str, Any], dict[str, Any] | None]]
Undo = Callable[[Session, EventBus, datetime, dict[str, Any]], None]


@dataclass(frozen=True)
class Spec:
    kind: str
    label: str
    risk: Risk
    params: type[BaseModel]
    describe: Describe
    execute: Execute
    undo: Undo | None = None
    confirm_word: str | None = None  # destructive: the word the user must type


def _workout_for(db: Session, now: datetime, ex: Exercise) -> int:
    w = workouts.active_workout(db)
    if w is None or w.day != now.date():
        w = workouts.start_workout(
            db, now, ex.section if ex.section in ("gym", "calisthenics") else "gym"
        )
    return w.id


def _set_items(p: LogSetP) -> list[SetItemP]:
    return [SetItemP(exercise=p.exercise, reps=p.reps, weight_kg=p.weight_kg, sets=p.sets), *p.more]


def _describe_set(db: Session, p: LogSetP) -> list[str]:
    lines = []
    for i, it in enumerate(_set_items(p)):
        ex = resolve_exercise(db, it.exercise)
        load = _kg(it.weight_kg) if it.weight_kg else "bodyweight"
        rpe = f" at RPE {p.rpe:g}" if p.rpe and i == 0 else ""
        lines.append(f"Log {it.sets} \u00d7 {it.reps} {ex.name}, {load}{rpe}, in today's session.")
    return lines


def _exec_set(
    db: Session, bus: EventBus, now: datetime, p: LogSetP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ids = []
    names = []
    wid = 0
    for i, it in enumerate(_set_items(p)):
        ex = resolve_exercise(db, it.exercise)
        wid = _workout_for(db, now, ex)
        names.append(ex.name)
        for _ in range(it.sets):
            row, _prev = workouts.log_set(
                db,
                bus,
                wid,
                SetIn(
                    exercise_id=ex.id,
                    weight_kg=it.weight_kg,
                    reps=it.reps,
                    rpe=p.rpe if i == 0 else None,
                ),
                now,
            )
            ids.append(row.id)
    return {"exercise": names[0], "exercises": names, "set_ids": ids, "workout_id": wid}, {
        "workout_id": wid,
        "set_ids": ids,
    }


def _undo_sets(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    for sid in u["set_ids"]:
        try:
            workouts.delete_set(db, bus, u["workout_id"], sid)
        except workouts.NotFound:
            continue


def _describe_hold(db: Session, p: LogHoldP) -> list[str]:
    ex = resolve_exercise(db, p.exercise)
    sets = f"{p.sets} \u00d7 " if p.sets > 1 else "a "
    plural = "s" if p.sets > 1 else ""
    return [f"Log {sets}{_secs(p.seconds)} {ex.name} hold{plural} in today's session."]


def _secs(s: int) -> str:
    """90 -> '1:30 min', 60 -> '1 min', 45 -> '45 s'."""
    if s < 60:
        return f"{s} s"
    m, r = divmod(s, 60)
    return f"{m} min" if not r else f"{m}:{r:02d} min"


def _exec_hold(
    db: Session, bus: EventBus, now: datetime, p: LogHoldP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    ex = resolve_exercise(db, p.exercise)
    wid = _workout_for(db, now, ex)
    ids = []
    for _ in range(p.sets):
        row, _ = workouts.log_set(
            db, bus, wid, SetIn(exercise_id=ex.id, duration_s=p.seconds, rpe=p.rpe), now
        )
        ids.append(row.id)
    return {"exercise": ex.name, "set_ids": ids}, {"workout_id": wid, "set_ids": ids}


def _describe_weight(db: Session, p: LogWeightP) -> list[str]:
    return [f"Add a weigh-in of {_kg(p.weight_kg)} for now."]


def _exec_weight(
    db: Session, bus: EventBus, now: datetime, p: LogWeightP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    out = body.log_metric(db, BodyMetricIn(weight_kg=p.weight_kg), now)
    return {"metric_id": out.id, "weight_kg": p.weight_kg}, {"metric_id": out.id}


def _undo_weight(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    body.delete_metric(db, u["metric_id"])


def _meal_foods(db: Session, p: LogMealP) -> list[tuple[Food, float]]:
    out: list[tuple[Food, float]] = []
    for it in p.items():
        for food in resolve_foods(db, it.food):
            out.append((food, it.portions))
    return out


def _describe_meal(db: Session, p: LogMealP) -> list[str]:
    foods = _meal_foods(db, p)
    if len(foods) == 1:
        food, portions = foods[0]
        return [f"Log {portions:g} \u00d7 {food.name} as {p.meal_type}."]
    kcal = sum(f.kcal * n for f, n in foods)
    lines = [f"Log one {p.meal_type} with {len(foods)} items (about {kcal:.0f} kcal):"]
    lines += [f"{n:g} \u00d7 {f.name} ({f.portion_label})" for f, n in foods]
    return lines


def _exec_meal(
    db: Session, bus: EventBus, now: datetime, p: LogMealP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    foods = _meal_foods(db, p)
    meal = nutrition.log_meal(
        db,
        bus,
        MealIn(
            meal_type=p.meal_type,
            items=[MealItemIn(food_id=f.id, portions=n) for f, n in foods],
        ),
        now,
    )
    return {"meal_id": meal.id, "food": foods[0][0].name, "foods": [f.name for f, _ in foods]}, {
        "meal_id": meal.id
    }


def _undo_meal(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    try:
        nutrition.delete_meal(db, u["meal_id"])
    except nutrition.NotFound:
        pass


def _describe_follow(db: Session, p: FollowProgramP) -> list[str]:
    _, name = resolve_program(db, p.program)
    cur = programs_service.active(db)
    then = f" (instead of {cur.program_key})" if cur else ""
    return [f"Follow {name}{then}. Your logged history stays as it is."]


def _exec_follow(
    db: Session, bus: EventBus, now: datetime, p: FollowProgramP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    key, name = resolve_program(db, p.program)
    cur = programs_service.active(db)
    prev = cur.program_key if cur else None
    programs_service.enroll(db, key, now)
    return {"program": name, "key": key}, {"previous": prev}


def _undo_follow(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    if u.get("previous"):
        programs_service.enroll(db, u["previous"], now)
    else:
        programs_service.leave(db, now)


def _describe_erase(db: Session, p: EraseDataP) -> list[str]:
    from app.models import Base  # noqa: F401  (all tables registered)
    from app.modules.workouts.models import Workout

    n = db.scalar(select(func.count(Workout.id))) or 0
    keep = "Your preferences are kept." if p.keep_preferences else "Preferences are reset too."
    return [
        f"Erase your profile, {n} workouts, meals, weigh-ins, XP and photos.",
        "A backup is made first; restore it from Settings > Backups.",
        f"The exercise library and food table stay. {keep}",
    ]


def _exec_erase(
    db: Session, bus: EventBus, now: datetime, p: EraseDataP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    # Run by the service with the request's data folder (see service.confirm).
    raise NotImplementedError


def _describe_add_food(db: Session, p: AddFoodP) -> list[str]:
    taken = db.scalars(select(Food).where(func.lower(Food.name) == p.name.strip().lower())).first()
    if taken is not None:
        raise ActionError(f"\u201c{taken.name}\u201d is already in the food list.")
    return [
        f"Add your own food \u201c{p.name.strip()}\u201d: {p.portion_label} "
        f"({p.portion_g:g} g) = {p.kcal:g} kcal, P {p.protein_g:g} g, C {p.carbs_g:g} g, "
        f"F {p.fat_g:g} g.",
        "It shows up in Fuel's search and the chat can log it.",
    ]


def _exec_add_food(
    db: Session, bus: EventBus, now: datetime, p: AddFoodP
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    food = nutrition.add_food(
        db,
        FoodIn(
            name=p.name.strip(),
            portion_label=p.portion_label,
            portion_g=p.portion_g,
            kcal=p.kcal,
            protein_g=p.protein_g,
            carbs_g=p.carbs_g,
            fat_g=p.fat_g,
        ),
    )
    return {"food_id": food.id, "name": food.name}, {"food_id": food.id}


def _undo_add_food(db: Session, bus: EventBus, now: datetime, u: dict[str, Any]) -> None:
    try:
        nutrition.delete_food(db, u["food_id"])
    except nutrition.NotFound:
        pass
    except nutrition.Conflict as e:  # already logged in a meal: it stays
        raise ActionError(str(e)) from e


SPECS: dict[str, Spec] = {
    s.kind: s
    for s in (
        Spec("log_set", "Log sets", "low", LogSetP, _describe_set, _exec_set, _undo_sets),
        Spec("log_hold", "Log a hold", "low", LogHoldP, _describe_hold, _exec_hold, _undo_sets),
        Spec(
            "log_weight",
            "Log a weigh-in",
            "low",
            LogWeightP,
            _describe_weight,
            _exec_weight,
            _undo_weight,
        ),
        Spec("log_meal", "Log food", "low", LogMealP, _describe_meal, _exec_meal, _undo_meal),
        Spec(
            "add_food",
            "Add your own food",
            "low",
            AddFoodP,
            _describe_add_food,
            _exec_add_food,
            _undo_add_food,
        ),
        Spec(
            "follow_program",
            "Switch program",
            "normal",
            FollowProgramP,
            _describe_follow,
            _exec_follow,
            _undo_follow,
        ),
        Spec(
            "erase_data",
            "Erase my data",
            "destructive",
            EraseDataP,
            _describe_erase,
            _exec_erase,
            None,
            confirm_word="ERASE",
        ),
    )
}


def dumps(d: Any) -> str:
    return json.dumps(d, default=str)
