"""v1.3: answers about the user's own numbers ("how many calories today", "what's my
streak", "what is my bmi"), read from the log, offline. The trainer says the number and
where it comes from; it never estimates one it doesn't have."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.trainer.schemas import ChatAction, ChatOut


def _out(reply: str, section: str | None = None, label: str | None = None) -> ChatOut:
    actions = (
        [ChatAction(kind="navigate", target=section, label=label or "Open")] if section else []
    )
    return ChatOut(reply=reply, mood="neutral", intent="my_data", source="rules", actions=actions)


def answer(db: Session, now: datetime, what: str, text: str = "") -> ChatOut:
    from app.modules.gamification import service as game
    from app.modules.nutrition import service as nutrition
    from app.modules.progress import body
    from app.modules.progress import service as progress

    today = now.date()
    p = progress.get_profile(db)
    if what in ("kcal", "protein"):
        t = nutrition.day_totals(db, today)
        target = progress.energy_for(p) if p is not None else None
        if what == "kcal":
            goal = f" of your {target.kcal_target:.0f} kcal target" if target else ""
            return _out(
                f"Today so far: {t.kcal:.0f} kcal{goal} (protein {t.protein_g:.0f} g).",
                "diet",
                "Open Fuel",
            )
        goal = f" of your {target.protein_target_g:.0f} g target" if target else ""
        return _out(f"Today so far: {t.protein_g:.0f} g protein{goal}.", "diet", "Open Fuel")
    if what == "meals":
        meals = nutrition.meals_on(db, today)
        if not meals:
            return _out(
                "Nothing logged today yet. Tell me what you ate, like "
                "\u201c2 idli and sambar for breakfast\u201d.",
                "diet",
                "Open Fuel",
            )
        parts = [
            f"{m.meal_type}: " + ", ".join(f"{i.portions:g} \u00d7 {i.food_name}" for i in m.items)
            for m in meals
        ]
        return _out("Today: " + "; ".join(parts) + ".", "diet", "Open Fuel")
    if what == "streak":
        s = game.streak(db, today)
        rest = (
            " Today is a planned rest day, so it is safe."
            if game.is_rest_day(db, today) and not s.active_today
            else ""
        )
        done = "" if s.active_today or rest else " Train today to keep it going."
        return _out(
            f"Your streak is {s.current} day{'s' if s.current != 1 else ''} (best "
            f"{s.best}).{rest}{done} Training days count; planned rest days never break "
            "it.",
            "dashboard",
            "Open Today",
        )
    if what in ("bmi", "weight"):
        w = body.latest_weight(db) or (p.weight_kg if p is not None else None)
        if w is None:
            return _out("Log a weigh-in first (say \u201cweight 60 kg\u201d).")
        if what == "weight":
            return _out(f"Your latest weight is {w:g} kg.", "progress", "Open Progress")
        if p is None or not p.height_cm:
            return _out(
                "I need your height for that; add it on Profile.", "profile", "Open Profile"
            )
        bmi = w / (p.height_cm / 100) ** 2
        band = (
            "below the healthy range (18.5-24.9)"
            if bmi < 18.5
            else "in the healthy range (18.5-24.9)"
            if bmi < 25
            else "above 25"
        )
        return _out(
            f"Your BMI is {bmi:.1f} ({w:g} kg, {p.height_cm:g} cm): {band}. BMI ignores "
            "muscle, so treat it as a rough guide."
        )
    if what == "progress":
        return _progress(db, now)
    if what == "max":
        return _best(db, text)
    return _out("Ask me about today's calories, protein, meals, your streak, BMI or progress.")


def _progress(db: Session, now: datetime) -> ChatOut:
    from app.modules.progress.models import BodyMetric
    from app.modules.workouts.models import Workout, WorkoutSet

    since = now.date() - timedelta(days=28)
    before = since - timedelta(days=28)

    def sessions(a: object, b: object) -> int:
        return int(
            db.scalar(
                select(func.count(func.distinct(Workout.day)))
                .join(WorkoutSet, WorkoutSet.workout_id == Workout.id)
                .where(Workout.day >= a, Workout.day < b)
            )
            or 0
        )

    recent, prior = sessions(since, now.date() + timedelta(days=1)), sessions(before, since)
    weights = [
        m.weight_kg
        for m in db.scalars(
            select(BodyMetric)
            .where(BodyMetric.measured_at >= now - timedelta(days=28))
            .order_by(BodyMetric.measured_at)
        )
    ]
    trend = ""
    if len(weights) >= 2:
        d = weights[-1] - weights[0]
        trend = (
            f" Weight {'+' if d >= 0 else ''}{d:.1f} kg over your last {len(weights)} weigh-ins."
        )
    if recent == 0:
        return _out(
            "No training logged in the last 4 weeks yet. One session is a start." + trend,
            "workout",
            "Open Train",
        )
    vs = f" (the 4 weeks before: {prior})" if prior else ""
    return _out(
        f"Last 4 weeks: {recent} training day{'s' if recent != 1 else ''}{vs}.{trend} "
        "Progress has the charts.",
        "progress",
        "Open Progress",
    )


def _best(db: Session, text: str) -> ChatOut:
    from app.modules.actions import registry
    from app.modules.workouts.models import WorkoutSet

    m = re.search(
        r"\b(?:max|best|pr|record)\b (?:for |on |in )?(?:my )?(.+)$", text.lower().strip(" ?")
    )
    name = m.group(1).strip() if m else ""
    if not name:
        return _out("Which exercise? Ask like \u201cwhat's my max pushups\u201d.")
    try:
        ex = registry.resolve_exercise(db, name)
    except registry.ActionError as e:
        return _out(str(e))
    if ex.measure == "hold":
        top = db.scalar(
            select(func.max(WorkoutSet.duration_s)).where(WorkoutSet.exercise_id == ex.id)
        )
        return _out(f"Your longest {ex.name}: {top} s." if top else f"No {ex.name} logged yet.")
    reps = db.scalar(
        select(func.max(WorkoutSet.reps)).where(
            WorkoutSet.exercise_id == ex.id,
            (WorkoutSet.weight_kg.is_(None)) | (WorkoutSet.weight_kg == 0),
        )
    )
    heavy = db.scalar(select(func.max(WorkoutSet.weight_kg)).where(WorkoutSet.exercise_id == ex.id))
    if not reps and not heavy:
        return _out(f"No {ex.name} logged yet. Log one like \u201c10 {ex.name.lower()}\u201d.")
    bits = []
    if reps:
        bits.append(f"{reps} reps in one set")
    if heavy:
        bits.append(f"{heavy:g} kg heaviest")
    return _out(f"Your best {ex.name}: " + ", ".join(bits) + ".", "progress", "Open Progress")
