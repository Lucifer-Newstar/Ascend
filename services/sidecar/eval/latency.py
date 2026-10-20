"""Latency on a one-year history: the engines alone, and the app's endpoints through the
real FastAPI app (SQLite, migrations, event bus), on a synthetic lifter's 365 days.

    cd services/sidecar && uv run python -m eval.latency --runs 30
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.main import create_app
from app.modules.intelligence import doses, personal, progression, recovery_service
from app.modules.intelligence import recovery as rec
from app.modules.workouts.models import Exercise, Workout, WorkoutSet
from eval import synth
from eval.recovery_eval import perfs_of, set_inputs

TOKEN = "latency"


def timed(fn: Callable[[], object], runs: int) -> dict[str, float]:
    fn()  # warm-up
    xs = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return {
        "p50_ms": round(statistics.median(xs), 1),
        "p95_ms": round(xs[min(len(xs) - 1, int(0.95 * len(xs)))], 1),
        "max_ms": round(xs[-1], 1),
    }


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def build(sessions: list[synth.Session], tmp: Path, clock: Clock) -> TestClient:
    settings = Settings(
        data_dir=tmp,
        db_url=f"sqlite:///{tmp / 'lat.db'}",
        token=TOKEN,
        ollama_host="http://127.0.0.1:9",
    )
    app = create_app(settings, clock=clock, outbox_interval=0)
    client = TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"})
    client.__enter__()
    client.put(
        "/profile",
        json={
            "name": "Lat",
            "age": 25,
            "sex": "male",
            "height_cm": 178,
            "weight_kg": 75,
            "goal": "maintain",
            "activity": "moderate",
        },
    )
    factory = app.state.session_factory
    with factory() as db:
        ids = {e.name: e.id for e in db.scalars(select(Exercise)).all()}
        for s in sessions:
            w = Workout(
                day=s.start.date(),
                section="gym",
                started_at=s.start,
                finished_at=s.start + timedelta(minutes=70),
                source="app",
            )
            db.add(w)
            db.flush()
            for ls in s.sets:
                if ls.reps <= 0:
                    continue
                db.add(
                    WorkoutSet(
                        workout_id=w.id,
                        exercise_id=ids[ls.exercise],
                        weight_kg=ls.weight_kg,
                        reps=ls.reps,
                        rpe=ls.rpe,
                        performed_at=ls.at,
                        is_pr=False,
                        e1rm=rec.clamp(ls.weight_kg * (1 + ls.reps / 30), 0, 1e6),
                    )
                )
        db.commit()
        doses.rebuild(db.connection())
        db.commit()
        recovery_service.refit(db, clock.now)
        db.commit()
    return client


def run(runs: int, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    user = synth.make_user(rng, 0, frequent=True)
    sessions = synth.simulate_self_coached(user, rng, 365)
    end = sessions[-1].start + timedelta(hours=20)
    sets = set_inputs(sessions)
    contribs = rec.contributions(sets)
    perfs = perfs_of(sessions)
    hist: dict[str, list[progression.SessionRec]] = {}
    for s in sessions:
        by: dict[str, list[progression.SetRec]] = {}
        for ls in s.sets:
            by.setdefault(ls.exercise, []).append(progression.SetRec(ls.reps, ls.weight_kg, ls.rpe))
        for ex, lst in by.items():
            hist.setdefault(ex, []).append(progression.SessionRec(s.start, tuple(lst)))
    bench_info = progression.ExerciseInfo(
        "Barbell Bench Press", "barbell", "reps", "compound", "push", 6, 12
    )
    recent = [c for c in contribs if c.at >= end - timedelta(days=rec.LOOKBACK_DAYS)]
    out: dict[str, object] = {
        "history": {"days": 365, "sessions": len(sessions), "sets": len(sets), "seed": seed},
        "engine": {
            "recovery states, 28-day window (19 muscles)": timed(
                lambda: rec.compute_from(recent, end), runs
            ),
            "personal factor fit, 365 days (6 groups)": timed(
                lambda: personal.fit(perfs, contribs), max(5, runs // 3)
            ),
            "progression target, 120 days of bench": timed(
                lambda: progression.next_target(bench_info, hist["Barbell Bench Press"][-40:], end),
                runs,
            ),
        },
    }
    clock = Clock(end)
    with tempfile.TemporaryDirectory() as tmp:
        client = build(sessions, Path(tmp), clock)
        bench = next(
            e["id"]
            for e in client.get("/exercises", params={"q": "Barbell Bench Press"}).json()
            if e["name"] == "Barbell Bench Press"
        )

        def finish() -> None:
            w = client.post("/workouts").json()["id"]
            client.post(
                f"/workouts/{w}/sets",
                json={"exercise_id": bench, "weight_kg": 60, "reps": 8, "rpe": 8},
            )
            clock.now += timedelta(minutes=50)
            client.post(f"/workouts/{w}/finish")
            clock.now += timedelta(hours=30)

        out["api"] = {
            "GET /muscles": timed(lambda: client.get("/muscles"), runs),
            "GET /intelligence/recovery": timed(lambda: client.get("/intelligence/recovery"), runs),
            "GET /intelligence/progression/{bench}": timed(
                lambda: client.get(f"/intelligence/progression/{bench}"), runs
            ),
            "GET /deload (stall check over every lift)": timed(lambda: client.get("/deload"), runs),
            "GET /intelligence/notices": timed(lambda: client.get("/intelligence/notices"), runs),
            "finish a workout (doses, refit, skills, quests)": timed(finish, max(5, runs // 3)),
        }
        client.__exit__(None, None, None)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    res = run(a.runs, a.seed)
    text = json.dumps(res, indent=2)
    print(text)
    if a.out:
        a.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
