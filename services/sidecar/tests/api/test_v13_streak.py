"""v1.3 streak rule (review S1 + S2): training keeps it, planned rest days are neutral."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.modules.gamification.streaks import compute_streak

MON = date(2026, 11, 2)


def days(*offsets: int) -> list[date]:
    return [MON + timedelta(days=o) for o in offsets]


def test_a_three_day_program_keeps_its_streak_over_rest_days() -> None:
    trained = days(0, 2, 4, 7, 9, 11)  # Mon/Wed/Fri for two weeks
    rest = days(1, 3, 5, 6, 8, 10, 12, 13)
    s = compute_streak(trained, MON + timedelta(days=12), rest_days=rest)
    assert s.current == 6 and s.best == 6 and s.reason_due is None


def test_without_rest_days_the_same_week_breaks_it() -> None:
    s = compute_streak(days(0, 2, 4, 7), MON + timedelta(days=7))
    assert s.current == 1


def test_a_missed_training_day_still_needs_its_reason() -> None:
    rest = days(1, 3, 5, 6)
    s = compute_streak(days(0, 2), MON + timedelta(days=5), rest_days=rest)
    assert s.current == 2 and s.reason_due == MON + timedelta(days=4)
    s = compute_streak(days(0, 2), MON + timedelta(days=7), rest_days=rest)
    assert s.current == 0  # Friday missed, no reason by Saturday


def test_training_on_a_rest_day_counts() -> None:
    s = compute_streak(days(0, 1, 2), MON + timedelta(days=2), rest_days=days(1))
    assert s.current == 3


def _train(client: TestClient) -> None:
    ex = next(e["id"] for e in client.get("/exercises", params={"q": "Push-up"}).json()
              if e["name"] == "Push-up")  # fmt: skip
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "reps": 10, "weight_kg": 0})
    client.post(f"/workouts/{w}/finish")


def test_the_followed_program_sets_the_rest_days(client: TestClient, profile, clock) -> None:
    # clock: Tue 20 Oct 2026. Bodyweight Starter trains 3 days a week.
    plan = next(
        p for p in client.get("/plans/programs").json() if p["key"] == "bodyweight_starter_3"
    )
    training = {d["weekday"] for d in plan["days"]}
    assert client.put("/plans/current", json={"program_key": plan["key"]}).status_code == 200
    for _ in range(14):
        if clock.now.weekday() in training:
            _train(client)
        clock.now += timedelta(days=1)
    s = client.get("/game/summary").json()
    assert s["streak"]["current"] >= 5 and s["streak"]["reason_due"] is None
    if clock.now.weekday() not in training:
        rest = s["quest"][0]
        assert rest["code"] == "rest_day" and rest["completed_at"] is not None


def test_a_rest_day_needs_no_reason(client: TestClient, profile, clock) -> None:
    plan = next(
        p for p in client.get("/plans/programs").json() if p["key"] == "bodyweight_starter_3"
    )
    training = {d["weekday"] for d in plan["days"]}
    client.put("/plans/current", json={"program_key": plan["key"]})
    while clock.now.weekday() in training:
        clock.now += timedelta(days=1)
    r = client.post(
        "/game/streak/reason", json={"day": clock.now.date().isoformat(), "reason": "x"}
    )
    assert r.status_code == 422 and "rest day" in r.text
