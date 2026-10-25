"""v1.3 welcome-back bonus (review M8): coming back after a miss is rewarded, once a week."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.modules.gamification.formulas import WELCOME_BACK_XP


def _train(client: TestClient, sets: int = 3) -> None:
    ex = next(e["id"] for e in client.get("/exercises", params={"q": "Push-up"}).json()
              if e["name"] == "Push-up")  # fmt: skip
    w = client.post("/workouts").json()["id"]
    for _ in range(sets):
        client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "reps": 10, "weight_kg": 0})
    client.post(f"/workouts/{w}/finish")


def _bonuses(client: TestClient) -> list[dict]:
    from sqlalchemy import select

    from app.modules.gamification.models import XpEvent

    db = client.app.state.session_factory()  # type: ignore[attr-defined]
    try:
        rows = db.scalars(select(XpEvent).where(XpEvent.source == "welcome_back")).all()
        return [{"day": r.day, "amount": r.amount} for r in rows]
    finally:
        db.close()


def test_the_first_session_after_a_miss_earns_the_bonus_once_a_week(
    client: TestClient, profile, clock
) -> None:
    clock.now -= timedelta(days=clock.now.weekday())  # Monday
    _train(client)
    assert _bonuses(client) == []  # first session ever: not a comeback
    clock.now += timedelta(days=2)  # Tuesday missed, no program: unplanned
    _train(client)
    got = _bonuses(client)
    assert len(got) == 1 and got[0]["amount"] == WELCOME_BACK_XP
    clock.now += timedelta(days=2)  # another miss in the same week
    _train(client)
    assert len(_bonuses(client)) == 1
    clock.now += timedelta(days=4)  # next week, after a gap
    _train(client)
    assert len(_bonuses(client)) == 2


def test_training_the_next_day_is_not_a_comeback(client: TestClient, profile, clock) -> None:
    _train(client)
    clock.now += timedelta(days=1)
    _train(client)
    assert _bonuses(client) == []


def test_planned_rest_days_are_not_a_miss(client: TestClient, profile, clock) -> None:
    plan = next(
        p for p in client.get("/plans/programs").json() if p["key"] == "bodyweight_starter_3"
    )
    training = sorted({d["weekday"] for d in plan["days"]})
    client.put("/plans/current", json={"program_key": plan["key"]})
    while clock.now.weekday() != training[0]:
        clock.now += timedelta(days=1)
    _train(client)
    clock.now += timedelta(days=training[1] - training[0])  # the next planned day
    _train(client)
    assert _bonuses(client) == []
