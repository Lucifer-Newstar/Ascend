"""Fill a database with realistic demo history: ~10 weeks of earlier gym training, then
a detailed fortnight.

The earlier weeks are the same push/pull/legs split with double progression up to the
fortnight's starting loads, so the progression engine has real trends, e1RM series and
personal recovery factors to work with. The fortnight adds the rest:
gym sessions, morning calisthenics (so the skill trees show mid-progress states),
Indian meals, morning weigh-ins and check-ins, tape measurements, a
few cardio and meditation sessions, and a goal weight for the Progress ETA.

Used for screenshots, UI work and demos. It goes through the real services
and event bus with a simulated clock, so XP, quests and muscle load are
exactly what the app would have produced live.

    uv run python -m app.devtools.seed_demo            # uses ASCEND_DATA_DIR / default DB
    uv run python -m app.devtools.seed_demo --days 14 --wipe
    uv run python -m app.devtools.seed_demo --history-weeks 0 --wipe   # fortnight only

Never run this against your real data: --wipe deletes everything first.
"""

from __future__ import annotations

import argparse
import math
import random
from datetime import datetime, time, timedelta
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.db import Base, make_engine, make_session_factory
from app.core.events import EventBus
from app.core.migrate import run_migrations
from app.main import build_bus
from app.modules.gamification import service as game
from app.modules.gamification.models import QuestItem
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.models import Food
from app.modules.nutrition.schemas import MealIn
from app.modules.progress import body, checkins
from app.modules.progress import service as progress
from app.modules.progress.schemas import (
    BodyMetricIn,
    CheckinIn,
    MeasurementIn,
    MeasurementSite,
    ProfileIn,
    SettingsIn,
)
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise, ExerciseMuscle
from app.modules.workouts.schemas import SetIn

# Push / pull / legs split: (exercise, start kg, reps)
SPLIT = {
    "push": [
        ("Barbell Bench Press", 60, 8),
        ("Incline Dumbbell Press", 22, 10),
        ("Lateral Raise", 8, 14),
        ("Triceps Pushdown", 25, 12),
    ],
    "pull": [
        ("Lat Pulldown", 50, 10),
        ("Barbell Row", 50, 8),
        ("Face Pull", 20, 15),
        ("Dumbbell Curl", 12, 10),
    ],
    "legs": [
        ("Back Squat", 70, 6),
        ("Romanian Deadlift", 60, 8),
        ("Leg Curl", 35, 12),
        ("Standing Calf Raise", 50, 12),
    ],
}
# Timed sessions on some rest days: (section, activity, minutes, metres or None, avg HR)
TIMED = {
    10: ("cardio", "Brisk Walking", 35, 3200, 112),
    6: ("cardio", "Stationary Bike", 25, None, 128),
    3: ("meditation", "Box Breathing", 10, None, None),
}
# Morning calisthenics: offset -> [(exercise, values)]; values are reps, or seconds for
# holds. Chosen so the skill trees show real mid-progress states: some steps unlocked,
# Pull-up one session short of 3x8 (logging 3x8 today unlocks the chest-to-bar step),
# and enough rising Tuck front lever sessions for a time-to-unlock estimate.
CALISTHENICS: dict[int, list[tuple[str, list[int]]]] = {
    13: [
        ("Dead Hang", [35, 35, 32]),
        ("Plank", [60, 60, 60]),
        ("Incline Push-up", [12, 12, 12]),
        ("Bodyweight Squat", [20, 20, 20]),
        ("Pike Push-up", [8, 8, 8]),
    ],
    11: [
        ("Dead Hang", [38, 36, 35]),
        ("Plank", [62, 60, 60]),
        ("Incline Push-up", [14, 13, 12]),
        ("Bodyweight Squat", [22, 20, 20]),
        ("Pike Push-up", [9, 8, 8]),
        ("Scapular Pull-up", [10, 10, 10]),
    ],
    9: [
        ("Scapular Pull-up", [12, 11, 10]),
        ("Negative Pull-up", [4, 4, 3]),
        ("Hollow Body Hold", [30, 30, 30]),
        ("Push-up", [10, 9, 8]),
        ("Headstand", [15, 15, 12]),
        ("Box Pistol Squat", [5, 5, 4]),
        ("Tuck Front Lever", [5, 5, 4]),
        ("Tuck L-sit", [6, 6, 5]),
    ],
    7: [
        ("Negative Pull-up", [5, 5, 5]),
        ("Hollow Body Hold", [32, 30, 30]),
        ("Push-up", [11, 10, 10]),
        ("Tuck L-sit", [8, 8, 6]),
        ("Pull-up", [5, 5, 4]),
        ("Headstand", [18, 16, 15]),
        ("Box Pistol Squat", [6, 5, 5]),
        ("Tuck Front Lever", [6, 6, 5]),
    ],
    5: [
        ("Negative Pull-up", [6, 5, 5]),
        ("Pull-up", [6, 6, 5]),
        ("Tuck Front Lever", [7, 7, 6]),
        ("Tuck L-sit", [10, 9, 8]),
        ("Push-up", [12, 11, 10]),
        ("Headstand", [20, 20, 18]),
        ("Chest Dip", [8, 7, 6]),
    ],
    3: [
        ("Pull-up", [7, 7, 6]),
        ("Tuck Front Lever", [8, 8, 7]),
        ("Tuck L-sit", [11, 10, 10]),
        ("Push-up", [13, 12, 12]),
        ("Box Pistol Squat", [7, 6, 6]),
        ("Chest Dip", [9, 8, 8]),
    ],
    1: [
        ("Pull-up", [8, 8, 8]),
        ("Tuck Front Lever", [10, 9, 9]),
        ("Tuck L-sit", [12, 12, 11]),
        ("Push-up", [14, 13, 13]),
        ("Headstand", [24, 22, 20]),
    ],
}
# Tape measurements at the start and near the end of the fortnight: site -> (first, last) cm
TAPE: dict[MeasurementSite, tuple[float, float]] = {
    "waist": (79.0, 79.5),
    "arm": (31.0, 31.5),
    "chest": (93.0, 94.0),
}
# Rest days are the gaps; today (offset 0) gets meals only.
SCHEDULE = {
    13: "push",
    12: "pull",
    11: "legs",
    9: "push",
    8: "pull",
    7: "legs",
    5: "push",
    4: "pull",
    2: "legs",
    1: "push",
}
MEALS: dict[str, list[list[tuple[str, float]]]] = {
    "breakfast": [
        [("Idli", 3), ("Sambar", 1), ("Coconut chutney", 1)],
        [("Plain dosa", 2), ("Sambar", 1), ("Tomato chutney", 1)],
        [("Ven pongal", 1), ("Medu vada", 1), ("Coconut chutney", 1)],
    ],
    "lunch": [
        [("Steamed rice", 1.5), ("Toor dal", 1), ("Mixed veg poriyal", 1), ("Curd (plain)", 1)],
        [("Chapati", 3), ("Chicken curry", 1), ("Curd (plain)", 1)],
        [("Chicken biryani", 1), ("Boiled egg", 1)],
    ],
    "snack": [
        [("Filter coffee (with milk, sugar)", 1), ("Sundal (chickpea)", 1)],
        [("Banana", 1), ("Buttermilk", 1)],
    ],
    "dinner": [
        [("Chapati", 3), ("Palak paneer", 1)],
        [("Steamed rice", 1), ("Fish curry", 1), ("Rasam", 1)],
        [("Plain dosa", 2), ("Peanut chutney", 1), ("Boiled egg", 2)],
    ],
}


# Load step per exercise in the earlier weeks (kg); everything else moves in 2.5 kg steps.
HISTORY_STEP = {
    "Back Squat": 5.0,
    "Romanian Deadlift": 5.0,
    "Lateral Raise": 1.0,
    "Dumbbell Curl": 1.0,
}
HISTORY_BLOCK_WEEKS = 2.5  # one load step per block; reps climb by 2 within a block


def seed_history(
    db: Session,
    bus: EventBus,
    ex: dict[str, int],
    rng: random.Random,
    today: datetime,
    days: int,
    weeks: int,
) -> int:
    """Earlier training before the fortnight: push, pull, legs, rest, repeated, with a
    missed session now and then. Loads rise one step per block of 2.5 weeks and reps
    climb within a block (double progression), ending at the fortnight's starting loads.
    Returns the number of sessions logged."""
    order: list[str | None] = ["push", "pull", "legs", None]
    sessions = 0
    for i, offset in enumerate(range(days + weeks * 7 - 1, days - 1, -1)):
        day = (today - timedelta(days=offset)).date()
        split = order[i % len(order)]
        if rng.random() < 0.7:
            checkins.record(
                db,
                bus,
                CheckinIn(
                    sleep=rng.choice([2, 3, 4, 4, 5]),
                    energy=rng.choice([3, 4, 4, 5]),
                    soreness=rng.choice(["none", "none", "some"]),
                    mood=rng.choice([3, 4, 5]),
                ),
                datetime.combine(day, time(7, 20)),
            )
        if split is None or rng.random() < 0.08:
            db.commit()
            continue
        weeks_left = (offset - days) / 7
        blocks = math.ceil(weeks_left / HISTORY_BLOCK_WEEKS - 1e-9)
        phase = (weeks_left % HISTORY_BLOCK_WEEKS) / HISTORY_BLOCK_WEEKS  # 1 = block start
        t = datetime.combine(day, time(18, 30))
        w = workouts.start_workout(db, t)
        for name, kg, reps in SPLIT[split]:
            step = HISTORY_STEP.get(name, 2.5)
            load = max(step, kg - step * blocks)
            target = reps + round(2 * (1 - phase))
            for set_no in range(3):
                t += timedelta(minutes=3)
                rpe = min(10.0, 7.5 + 0.5 * set_no + rng.choice([-0.5, 0.0, 0.0, 0.5]))
                got = target - (1 if set_no == 2 and rng.random() < 0.3 else 0)
                workouts.log_set(
                    db, bus, w.id, SetIn(exercise_id=ex[name], weight_kg=load, reps=got, rpe=rpe), t
                )
        workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=5))
        sessions += 1
        db.commit()
    return sessions


# Earlier weeks' eating (tdee-v1 demo, ADR-0018): a lean bulk logged on about 9 days in 10,
# with weigh-ins on about 85 % of mornings. Weight follows the intake against a fixed
# expenditure, so the adaptive estimate has something real to learn before the fortnight.
DIET_TRUE_TDEE_KCAL = 2550.0
DIET_INTAKE_KCAL = 2700.0


def meal_scale(db: Session) -> float:
    """Portion multiplier that makes an average demo day about DIET_INTAKE_KCAL."""
    kcal_of = {f.name: f.kcal for f in db.scalars(select(Food)).all()}
    mean_day = sum(
        sum(sum(kcal_of[n] * p for n, p in opt) for opt in MEALS[m]) / len(MEALS[m])
        for m in ("breakfast", "lunch", "snack", "dinner")
    )
    return DIET_INTAKE_KCAL / mean_day


def seed_diet_history(
    db: Session,
    bus: EventBus,
    foods: dict[str, int],
    rng: random.Random,
    today: datetime,
    days: int,
    weeks: int,
) -> int:
    """Meals and weigh-ins for the `weeks` before the detailed fortnight. Returns the number
    of days with meals logged."""
    kcal_of = {f.name: f.kcal for f in db.scalars(select(Food)).all()}
    scale = meal_scale(db)
    plan = []
    weight = 0.0
    for offset in range(days + weeks * 7 - 1, days - 1, -1):
        day = (today - timedelta(days=offset)).date()
        meals = []
        for meal_type in ("breakfast", "lunch", "snack", "dinner"):
            items = [
                (n, max(0.5, round(p * scale * 2) / 2)) for n, p in rng.choice(MEALS[meal_type])
            ]
            meals.append((meal_type, items))
        eaten = sum(kcal_of[n] * p for _, items in meals for n, p in items)
        plan.append((day, meals, weight, rng.random() < 0.9, rng.random() < 0.85))
        weight += (eaten - DIET_TRUE_TDEE_KCAL) / 7700
    shift = 67.9 - weight  # the fortnight starts at about 68 kg
    logged = 0
    for day, meals, w, log, weigh in plan:
        if weigh:
            kg = round(w + shift + rng.uniform(-0.35, 0.35), 1)
            t = datetime.combine(day, time(7, 10))
            body.log_metric(db, BodyMetricIn(measured_at=t, weight_kg=kg), t)
        if log:
            logged += 1
            for k, (meal_type, items) in enumerate(meals):
                nutrition.log_meal(
                    db,
                    bus,
                    MealIn.model_validate(
                        {
                            "meal_type": meal_type,
                            "items": [{"food_id": foods[n], "portions": p} for n, p in items],
                        }
                    ),
                    datetime.combine(day, time((8, 13, 17, 20)[k], 30)),
                )
        db.commit()
    return logged


def seed(days: int, wipe: bool, history_weeks: int = 10) -> None:
    settings = load_settings()
    url = settings.resolved_db_url
    run_migrations(url)
    engine = make_engine(url)
    factory = make_session_factory(engine)
    bus = build_bus()
    rng = random.Random(42)
    today = datetime.now().replace(second=0, microsecond=0)

    with factory() as db:
        if wipe:
            for table in reversed(Base.metadata.sorted_tables):
                if table.name not in ("exercises", "exercise_muscles", "foods", "alembic_version"):
                    db.execute(table.delete())
            # The library stays; exercises the user added are user data and go too.
            custom_ids = select(Exercise.id).where(Exercise.is_custom.is_(True))
            db.execute(delete(ExerciseMuscle).where(ExerciseMuscle.exercise_id.in_(custom_ids)))
            db.execute(delete(Exercise).where(Exercise.is_custom.is_(True)))
            db.commit()
        progress.upsert_profile(
            db,
            ProfileIn(
                name="Navin",
                age=21,
                sex="male",
                height_cm=174,
                weight_kg=68,
                goal="bulk",
                activity="moderate",
                target_weight_kg=72,
            ),
        )
        # The demo trains a push/pull/legs split about five days a week.
        progress.update_settings(db, SettingsIn(sessions_per_week=5))
        ex = {e.name: e.id for e in db.scalars(select(Exercise)).all()}
        holds = {e.name for e in db.scalars(select(Exercise).where(Exercise.measure == "hold"))}
        foods = {f.name: f.id for f in db.scalars(select(Food)).all()}
        portion_scale = meal_scale(db)  # a lean bulk's portions (about 2,700 kcal a day)
        earlier = seed_history(db, bus, ex, rng, today, days, history_weeks) if history_weeks else 0
        diet_days = (
            seed_diet_history(db, bus, foods, random.Random(7), today, days, history_weeks)
            if history_weeks
            else 0
        )

        for offset in range(days - 1, -1, -1):
            day = (today - timedelta(days=offset)).date()

            def at(h: int, m: int, _day=day) -> datetime:
                return datetime.combine(_day, time(h, m))

            game.ensure_quest(db, at(7, 0))
            # Morning weigh-in: a slow bulk (~0.3 kg/week) with day-to-day water noise.
            if offset > 0 and rng.random() < 0.85:
                kg = 68.0 + 0.045 * (days - offset) + rng.uniform(-0.35, 0.35)
                body.log_metric(
                    db, BodyMetricIn(measured_at=at(7, 10), weight_kg=round(kg, 1)), at(7, 10)
                )
            if offset in (days - 1, 1):
                for site, (first, last) in TAPE.items():
                    cm = first if offset == days - 1 else last
                    body.log_measurement(
                        db, MeasurementIn(measured_at=at(7, 15), site=site, cm=cm), at(7, 15)
                    )
            if offset > 0:  # today is left for the user's own check-in
                sore: Literal["none", "some"] = (
                    "some" if SCHEDULE.get(offset + 1) == "legs" else "none"
                )
                checkins.record(
                    db,
                    bus,
                    CheckinIn(
                        sleep=rng.choice([3, 4, 4, 5]),
                        energy=rng.choice([3, 4, 4, 5]),
                        soreness=sore,
                        mood=rng.choice([3, 4, 5]),
                    ),
                    at(7, 20),
                )
            plan = [
                ("breakfast", at(8, 15)),
                ("lunch", at(13, 20)),
                ("snack", at(17, 0)),
                ("dinner", at(20, 45)),
            ]
            if offset == 0:
                plan = [p for p in plan if p[1] <= today]
            for meal_type, t in plan:
                if offset > 0 and meal_type == "snack" and rng.random() < 0.5:
                    continue
                items = [
                    (n, max(0.5, round(p * portion_scale * 2) / 2))
                    for n, p in rng.choice(MEALS[meal_type])
                ]
                nutrition.log_meal(
                    db,
                    bus,
                    MealIn.model_validate(
                        {
                            "meal_type": meal_type,
                            "items": [{"food_id": foods[n], "portions": p} for n, p in items],
                        }
                    ),
                    t,
                )

            cali = CALISTHENICS.get(offset)
            if cali:
                t = at(7, 30)
                w = workouts.start_workout(db, t, section="calisthenics")
                for name, values in cali:
                    for set_no, value in enumerate(values):
                        t += timedelta(minutes=2)
                        body_ = (
                            SetIn(exercise_id=ex[name], duration_s=value, rpe=8.0 + set_no * 0.5)
                            if name in holds
                            else SetIn(exercise_id=ex[name], reps=value, rpe=8.0 + set_no * 0.5)
                        )
                        workouts.log_set(db, bus, w.id, body_, t)
                workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=3))

            split = SCHEDULE.get(offset)
            if split:
                week = (13 - offset) // 4  # small progressive overload across the fortnight
                t = at(18, 30)
                w = workouts.start_workout(db, t)
                for name, kg, reps in SPLIT[split]:
                    for set_no in range(3):
                        t += timedelta(minutes=3)
                        rpe = [7.0, 8.0, 9.0][set_no]
                        workouts.log_set(
                            db,
                            bus,
                            w.id,
                            SetIn(
                                exercise_id=ex[name], weight_kg=kg + 2.5 * week, reps=reps, rpe=rpe
                            ),
                            t,
                        )
                workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=5))

            timed = TIMED.get(offset)
            if timed:
                section, name, minutes, metres, hr = timed
                t = at(7, 45)
                w = workouts.start_workout(db, t, section=section)
                workouts.log_set(
                    db,
                    bus,
                    w.id,
                    SetIn(
                        exercise_id=ex[name],
                        duration_s=minutes * 60,
                        distance_m=metres,
                        avg_hr=hr,
                        rpe=5.0 if section == "cardio" else None,
                    ),
                    t + timedelta(minutes=minutes),
                )
                workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=minutes + 1))

            if offset > 0:
                for q in db.scalars(select(QuestItem).where(QuestItem.day == day)).all():
                    if q.metric == "manual" and not q.completed_at and rng.random() < 0.75:
                        game.complete_manual(db, bus, q.id, at(21, 30))
            db.commit()
    print(
        f"seeded {days} days of demo data (+{history_weeks} earlier weeks, {earlier} gym sessions, "
        f"{diet_days} days of meals) into {url}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument(
        "--history-weeks", type=int, default=10, help="earlier PPL weeks before the fortnight"
    )
    parser.add_argument("--wipe", action="store_true", help="delete existing user data first")
    args = parser.parse_args()
    seed(args.days, args.wipe, args.history_weeks)


if __name__ == "__main__":
    main()
