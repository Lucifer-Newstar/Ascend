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


# --- solo-safe martial arts (item 9) ------------------------------------------------------

UNSAFE = (
    "bjj",
    "rolling",
    "sparring",
    "partner",
    "pad work",
    "kalari",
    "sword",
    "stick",
    "throw",
    "lock",
    "choke",
)


def test_martial_arts_is_its_own_solo_safe_category(client: TestClient) -> None:
    drills = client.get("/exercises", params={"section": "martial_arts"}).json()
    names = {d["name"] for d in drills}
    for name in (
        "Jab-Cross Shadow Drill",
        "Teep Push Kick Drill",
        "Horse Stance Hold",
        "Sprawl Drill",
    ):
        assert name in names
    assert len(drills) >= 20
    for d in drills:
        assert not any(w in d["name"].lower() for w in UNSAFE), d["name"]
        assert d["time_based"] is True
    detail = client.get(
        f"/exercises/{next(d['id'] for d in drills if d['name'] == 'Front Kick Drill')}"
    ).json()
    assert len(detail["instructions"]) >= 3
    assert detail["muscles"]
