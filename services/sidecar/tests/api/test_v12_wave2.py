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


# --- boss ladder (item 7) -----------------------------------------------------------------


def test_the_boss_ladder_lists_every_boss_by_tier_then_the_seasons(client: TestClient) -> None:
    ladder = client.get("/game/bosses").json()
    assert len(ladder) == 16
    regular = [b for b in ladder if not b["seasonal"]]
    order = "EDCBAS"
    assert [order.index(b["tier"]) for b in regular] == sorted(
        order.index(b["tier"]) for b in regular
    )
    assert regular[-1]["name"] == "Bone Titan"
    seasonal = {b["name"]: b for b in ladder if b["seasonal"]}
    assert set(seasonal) == {
        "Winter Wraith",
        "Shadow Sovereign",
        "Monsoon Serpent",
        "Harvest Colossus",
    }
    assert all(b["drop"] for b in seasonal.values()) and all(b["beaten"] == 0 for b in ladder)


def test_the_weekly_boss_says_its_tier_and_season(client: TestClient, profile, clock) -> None:
    b = client.get("/game/boss").json()
    assert b["tier"] in "EDCBAS" and b["category"] in (
        "strength",
        "calisthenics",
        "cardio",
        "martial_arts",
    )
    if b["seasonal"]:
        assert b["season"] and b["drop"] and b["season_ends"] >= b["week_end"]
    else:
        assert b["season"] is None and b["drop"] is None


# --- avatar and cosmetics (items 4-6) -----------------------------------------------------


def test_the_avatar_follows_the_profile_until_you_pick_one(client: TestClient, profile) -> None:
    s = client.get("/settings").json()
    assert s["avatar"] == "male" and s["outfit"] == "" and s["themed_cosmetics"] is True
    s = client.put(
        "/settings", json={"avatar": "female", "outfit": "outfit_ronin", "pet": "pet_tiger_cub"}
    ).json()
    assert (s["avatar"], s["outfit"], s["pet"], s["relic"]) == (
        "female",
        "outfit_ronin",
        "pet_tiger_cub",
        "",
    )
    s = client.put("/settings", json={"outfit": "", "themed_cosmetics": False}).json()
    assert s["outfit"] == "" and s["themed_cosmetics"] is False
    assert client.put("/settings", json={"outfit": "../evil"}).status_code == 422


def test_reminders_are_on_until_switched_off(client: TestClient) -> None:
    assert client.get("/settings").json()["reminders"] is True
    assert client.put("/settings", json={"reminders": False}).json()["reminders"] is False
    assert client.get("/settings").json()["reminders"] is False
