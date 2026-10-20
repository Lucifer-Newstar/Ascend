"""log_set and finish_workout in one long-lived session (seeder, importers, scripts)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.db import make_engine, make_session_factory
from app.core.migrate import run_migrations
from app.main import build_bus
from app.modules.workouts import service
from app.modules.workouts.models import Exercise
from app.modules.workouts.schemas import SetIn


def test_sets_logged_in_the_same_session_are_visible_to_finish(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'one-session.db'}"
    run_migrations(url)
    factory = make_session_factory(make_engine(url))
    bus = build_bus()
    t = datetime(2026, 10, 20, 7, 0)
    with factory() as db:
        walk = db.scalars(select(Exercise).where(Exercise.name == "Brisk Walking")).one()
        bench = db.scalars(select(Exercise).where(Exercise.name == "Barbell Bench Press")).one()

        w = service.start_workout(db, t, section="cardio")
        assert w.sets == []  # collection loaded empty before the first set
        service.log_set(db, bus, w.id, SetIn(exercise_id=walk.id, duration_s=1800), t)
        _, minutes, _ = service.finish_workout(db, bus, w.id, t + timedelta(minutes=31))
        assert minutes == 31.0
        assert len(w.sets) == 1

        g = service.start_workout(db, t + timedelta(hours=10))
        for i in range(3):
            service.log_set(
                db,
                bus,
                g.id,
                SetIn(exercise_id=bench.id, weight_kg=60, reps=8),
                t + timedelta(hours=10, minutes=3 * i),
            )
        service.finish_workout(db, bus, g.id, t + timedelta(hours=11))
        assert [s.weight_kg for s in g.sets] == [60, 60, 60]
