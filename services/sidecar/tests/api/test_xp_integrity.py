"""Review L8: XP follows edits, and corrections can't free up today's daily cap."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from app.modules.gamification import formulas as f
from app.modules.gamification.models import XpEvent


def _ex(client, q: str) -> int:
    return next(e["id"] for e in client.get("/exercises", params={"q": q}).json())


def _xp(client, **where) -> int:
    with client.app.state.session_factory() as db:
        stmt = select(func.coalesce(func.sum(XpEvent.amount), 0))
        for k, v in where.items():
            stmt = stmt.where(getattr(XpEvent, k) == v)
        return int(db.scalar(stmt) or 0)


def _log(client, w: int, **body) -> int:
    r = client.post(f"/workouts/{w}/sets", json=body)
    assert r.status_code == 201, r.text
    return r.json()["set"]["id"]


def test_lowering_rpe_after_logging_takes_the_extra_xp_back(client, profile) -> None:
    squat = _ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    sid = _log(client, w, exercise_id=squat, weight_kg=60, reps=5, rpe=10)
    assert _xp(client, source="set", ref_id=sid) == f.set_xp(10)
    assert client.patch(f"/workouts/{w}/sets/{sid}", json={"rpe": 1}).status_code == 200
    assert _xp(client, source="set", ref_id=sid) == f.set_xp(1)


def test_shortening_a_run_after_logging_takes_the_extra_xp_back(client, profile) -> None:
    run = _ex(client, "Running")
    w = client.post("/workouts").json()["id"]
    sid = _log(client, w, exercise_id=run, duration_s=6 * 3600)
    assert _xp(client, source="set", ref_id=sid) > f.timed_set_xp(60, "cardio")
    assert client.patch(f"/workouts/{w}/sets/{sid}", json={"duration_s": 60}).status_code == 200
    assert _xp(client, source="set", ref_id=sid) == f.timed_set_xp(60, "cardio")


def test_an_edit_never_adds_xp(client, profile) -> None:
    squat = _ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    sid = _log(client, w, exercise_id=squat, weight_kg=60, reps=5, rpe=1)
    client.patch(f"/workouts/{w}/sets/{sid}", json={"rpe": 10})
    assert _xp(client, source="set", ref_id=sid) == f.set_xp(1)


def test_deleting_an_old_set_books_the_correction_on_its_own_day(client, clock, profile) -> None:
    squat = _ex(client, "Back Squat")
    day1 = clock.now.date()
    w = client.post("/workouts").json()["id"]
    sid = _log(client, w, exercise_id=squat, weight_kg=60, reps=5)
    client.post(f"/workouts/{w}/finish")
    clock.now += timedelta(days=1)
    day2 = clock.now.date()
    assert client.delete(f"/workouts/{w}/sets/{sid}").status_code == 204
    # Nothing was earned today, so nothing may be taken off today's count (which would
    # leave extra room under today's daily cap).
    assert _xp(client, day=day2) == 0
    assert _xp(client, source="set", ref_id=sid) == 0
    assert _xp(client, source="set", day=day1) == 0


def test_an_edit_that_ends_another_sets_pr_takes_that_pr_xp_back(client, clock, profile) -> None:
    squat = _ex(client, "Back Squat")
    w1 = client.post("/workouts").json()["id"]
    a = _log(client, w1, exercise_id=squat, weight_kg=100, reps=5)
    client.post(f"/workouts/{w1}/finish")
    clock.now += timedelta(days=1)
    w2 = client.post("/workouts").json()["id"]
    b = _log(client, w2, exercise_id=squat, weight_kg=105, reps=5)
    client.post(f"/workouts/{w2}/finish")
    assert _xp(client, source="pr", ref_id=b) == f.PR_XP
    clock.now += timedelta(days=1)
    # The older set was really heavier: set B is no longer a PR.
    assert client.patch(f"/workouts/{w1}/sets/{a}", json={"weight_kg": 110}).status_code == 200
    assert _xp(client, source="pr", ref_id=b) == 0
