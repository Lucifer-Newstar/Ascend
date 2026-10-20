"""Fill a database with ~2 weeks of realistic demo history.

Used for screenshots, UI work and demos. It goes through the real services
and event bus with a simulated clock, so XP, quests and muscle load are
exactly what the app would have produced live.

    uv run python -m app.devtools.seed_demo            # uses ASCEND_DATA_DIR / default DB
    uv run python -m app.devtools.seed_demo --days 14 --wipe

Never run this against your real data: --wipe deletes everything first.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, time, timedelta

from sqlalchemy import select

from app.core.config import load_settings
from app.core.db import Base, make_engine, make_session_factory
from app.core.migrate import run_migrations
from app.main import build_bus
from app.modules.gamification import service as game
from app.modules.gamification.models import QuestItem
from app.modules.nutrition import service as nutrition
from app.modules.nutrition.models import Food
from app.modules.nutrition.schemas import MealIn, MealItemIn
from app.modules.progress import service as progress
from app.modules.progress.schemas import ProfileIn
from app.modules.workouts import service as workouts
from app.modules.workouts.models import Exercise
from app.modules.workouts.schemas import SetIn

# Push / pull / legs split: (exercise, start kg, reps)
SPLIT = {
    "push": [("Barbell Bench Press", 60, 8), ("Incline Dumbbell Press", 22, 10),
             ("Lateral Raise", 8, 14), ("Triceps Pushdown", 25, 12)],
    "pull": [("Lat Pulldown", 50, 10), ("Barbell Row", 50, 8), ("Face Pull", 20, 15),
             ("Dumbbell Curl", 12, 10)],
    "legs": [("Back Squat", 70, 6), ("Romanian Deadlift", 60, 8), ("Leg Curl", 35, 12),
             ("Standing Calf Raise", 50, 12)],
}
# Rest days are the gaps; today (offset 0) gets meals only.
SCHEDULE = {13: "push", 12: "pull", 11: "legs", 9: "push", 8: "pull", 7: "legs",
            5: "push", 4: "pull", 2: "legs", 1: "push"}
MEALS = {
    "breakfast": [[("Idli", 3), ("Sambar", 1), ("Coconut chutney", 1)],
                  [("Plain dosa", 2), ("Sambar", 1), ("Tomato chutney", 1)],
                  [("Ven pongal", 1), ("Medu vada", 1), ("Coconut chutney", 1)]],
    "lunch": [[("Steamed rice", 1.5), ("Toor dal", 1), ("Mixed veg poriyal", 1), ("Curd (plain)", 1)],
              [("Chapati", 3), ("Chicken curry", 1), ("Curd (plain)", 1)],
              [("Chicken biryani", 1), ("Boiled egg", 1)]],
    "snack": [[("Filter coffee (with milk, sugar)", 1), ("Sundal (chickpea)", 1)],
              [("Banana", 1), ("Buttermilk", 1)]],
    "dinner": [[("Chapati", 3), ("Palak paneer", 1)],
               [("Steamed rice", 1), ("Fish curry", 1), ("Rasam", 1)],
               [("Plain dosa", 2), ("Peanut chutney", 1), ("Boiled egg", 2)]],
}


def seed(days: int, wipe: bool) -> None:
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
            db.commit()
        progress.upsert_profile(db, ProfileIn(name="Navin", age=21, sex="male", height_cm=174,
                                              weight_kg=68, goal="bulk", activity="moderate"))
        ex = {e.name: e.id for e in db.scalars(select(Exercise)).all()}
        foods = {f.name: f.id for f in db.scalars(select(Food)).all()}

        for offset in range(days - 1, -1, -1):
            day = (today - timedelta(days=offset)).date()

            def at(h: int, m: int, _day=day) -> datetime:
                return datetime.combine(_day, time(h, m))

            game.ensure_quest(db, at(7, 0))
            plan = [("breakfast", at(8, 15)), ("lunch", at(13, 20)), ("snack", at(17, 0)),
                    ("dinner", at(20, 45))]
            if offset == 0:
                plan = [p for p in plan if p[1] <= today]
            for meal_type, t in plan:
                if offset > 0 and meal_type == "snack" and rng.random() < 0.5:
                    continue
                items = rng.choice(MEALS[meal_type])
                nutrition.log_meal(db, bus, MealIn(meal_type=meal_type, items=[  # type: ignore[arg-type]
                    MealItemIn(food_id=foods[n], portions=p) for n, p in items]), t)

            split = SCHEDULE.get(offset)
            if split:
                week = (13 - offset) // 4  # small progressive overload across the fortnight
                t = at(18, 30)
                w = workouts.start_workout(db, t)
                for name, kg, reps in SPLIT[split]:
                    for set_no in range(3):
                        t += timedelta(minutes=3)
                        rpe = [7.0, 8.0, 9.0][set_no]
                        workouts.log_set(db, bus, w.id, SetIn(
                            exercise_id=ex[name], weight_kg=kg + 2.5 * week, reps=reps, rpe=rpe), t)
                workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=5))

            if offset > 0:
                for q in db.scalars(select(QuestItem).where(QuestItem.day == day)).all():
                    if q.metric == "manual" and not q.completed_at and rng.random() < 0.75:
                        game.complete_manual(db, bus, q.id, at(21, 30))
            db.commit()
    print(f"seeded {days} days of demo data into {url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--wipe", action="store_true", help="delete existing user data first")
    args = parser.parse_args()
    seed(args.days, args.wipe)


if __name__ == "__main__":
    main()
