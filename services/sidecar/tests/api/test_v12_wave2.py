"""v1.2 wave 2: the new sidecar features (streak reasons, seasonal bosses, cosmetics...)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient


def weigh(client: TestClient, kg: float = 60.0) -> None:
    assert client.post("/body-metrics", json={"weight_kg": kg}).status_code in (200, 201)


def streak(client: TestClient) -> dict:
    return client.get("/game/summary").json()["streak"]


# --- streak reasons (item 12) ------------------------------------------------------------


def test_a_reason_by_the_next_day_keeps_the_streak(client: TestClient, clock) -> None:
    weigh(client)
    clock.now += timedelta(days=1)
    weigh(client)
    clock.now += timedelta(days=2)  # one day missed in between
    s = streak(client)
    missed = (clock.now - timedelta(days=1)).date().isoformat()
    assert s["reason_due"] == missed and s["current"] == 2
    r = client.post("/game/streak/reason", json={"day": missed, "reason": "fever, stayed in bed"})
    assert r.status_code == 200, r.text
    assert r.json()["excused"] == 1 and r.json()["reason_due"] is None
    weigh(client)
    s = streak(client)
    assert s["current"] == 3 and s["excused"] == 1


def test_no_reason_or_two_missed_days_reset(client: TestClient, clock) -> None:
    weigh(client)
    clock.now += timedelta(days=1)
    weigh(client)
    clock.now += timedelta(days=3)  # two days missed
    weigh(client)
    assert streak(client)["current"] == 1
    old = (clock.now - timedelta(days=2)).date().isoformat()
    r = client.post("/game/streak/reason", json={"day": old, "reason": "busy"})
    assert r.status_code == 422  # too late: only yesterday can still get a reason


def test_a_day_that_counts_needs_no_reason(client: TestClient, clock) -> None:
    weigh(client)
    today = clock.now.date().isoformat()
    r = client.post("/game/streak/reason", json={"day": today, "reason": "x"})
    assert r.status_code == 422
