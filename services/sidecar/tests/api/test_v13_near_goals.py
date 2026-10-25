"""v1.3 wave 3: what the game summary says beside the streak (review S5, S6, 1.3, 1.6)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient


def _train(client: TestClient) -> None:
    ex = next(e["id"] for e in client.get("/exercises", params={"q": "Push-up"}).json()
              if e["name"] == "Push-up")  # fmt: skip
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "reps": 10, "weight_kg": 0})
    client.post(f"/workouts/{w}/finish")


def test_lifetime_sessions_and_best_streak_survive_a_reset(
    client: TestClient, profile, clock
) -> None:
    for _ in range(3):
        _train(client)
        clock.now += timedelta(days=1)
    clock.now += timedelta(days=3)  # two unexcused misses: the streak resets
    s = client.get("/game/summary").json()["streak"]
    assert s["current"] == 0 and s["best"] == 3
    assert s["lifetime_sessions"] == 3 and s["next_milestone"] == 5


def test_rest_today_follows_the_program(client: TestClient, profile, clock) -> None:
    plan = next(
        p for p in client.get("/plans/programs").json() if p["key"] == "bodyweight_starter_3"
    )
    training = {d["weekday"] for d in plan["days"]}
    client.put("/plans/current", json={"program_key": plan["key"]})
    s = client.get("/game/summary").json()["streak"]
    assert s["rest_today"] is (clock.now.weekday() not in training)
    assert s["week_target"] == 3
    while clock.now.weekday() in training:
        clock.now += timedelta(days=1)
    assert client.get("/game/summary").json()["streak"]["rest_today"] is True


def test_weeks_in_a_row_count_weeks_with_the_plan_met(client: TestClient, profile, clock) -> None:
    client.put("/settings", json={"sessions_per_week": 2})
    clock.now -= timedelta(days=clock.now.weekday())  # Monday
    for _week in range(2):
        _train(client)
        clock.now += timedelta(days=2)
        _train(client)
        clock.now += timedelta(days=5)
    s = client.get("/game/summary").json()["streak"]
    assert s["week_target"] == 2 and s["weeks_in_a_row"] == 2


def test_the_xp_summary_has_a_sub_rank_and_the_next_one(client: TestClient, profile) -> None:
    xp = client.get("/game/summary").json()["xp"]
    assert xp["sub_rank"] == "E1" and xp["next_sub_rank"] == "E2"
    assert xp["next_sub_rank_level"] == 4
