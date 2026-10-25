"""v1.2 wave 2: the new sidecar features (streak reasons, seasonal bosses, cosmetics...)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient


def weigh(client: TestClient, kg: float = 60.0) -> None:
    assert client.post("/body-metrics", json={"weight_kg": kg}).status_code in (200, 201)


def streak(client: TestClient) -> dict:
    return client.get("/game/summary").json()["streak"]


def train(client: TestClient) -> None:
    """v1.3: only training keeps the streak, so these tests log one set (not a weigh-in)."""
    ex = next(e["id"] for e in client.get("/exercises", params={"q": "Push-up"}).json()
              if e["name"] == "Push-up")  # fmt: skip
    w = client.post("/workouts").json()["id"]
    r = client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "reps": 10, "weight_kg": 0})
    assert r.status_code in (200, 201), r.text
    assert client.post(f"/workouts/{w}/finish").status_code == 200


# --- streak reasons (item 12) ------------------------------------------------------------


def test_a_reason_by_the_next_day_keeps_the_streak(client: TestClient, clock) -> None:
    train(client)
    clock.now += timedelta(days=1)
    train(client)
    clock.now += timedelta(days=2)  # one day missed in between
    s = streak(client)
    missed = (clock.now - timedelta(days=1)).date().isoformat()
    assert s["reason_due"] == missed and s["current"] == 2
    r = client.post("/game/streak/reason", json={"day": missed, "reason": "fever, stayed in bed"})
    assert r.status_code == 200, r.text
    assert r.json()["excused"] == 1 and r.json()["reason_due"] is None
    train(client)
    s = streak(client)
    assert s["current"] == 3 and s["excused"] == 1


def test_no_reason_or_two_missed_days_reset(client: TestClient, clock) -> None:
    train(client)
    clock.now += timedelta(days=1)
    train(client)
    clock.now += timedelta(days=3)  # two days missed
    train(client)
    assert streak(client)["current"] == 1
    old = (clock.now - timedelta(days=2)).date().isoformat()
    r = client.post("/game/streak/reason", json={"day": old, "reason": "busy"})
    assert r.status_code == 422  # too late: only yesterday can still get a reason


def test_a_day_that_counts_needs_no_reason(client: TestClient, clock) -> None:
    train(client)
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


# --- programs v2 (items 10-11) ------------------------------------------------------------

SECTIONS = ("gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation")


def test_every_section_has_programs_tagged_by_level(client: TestClient) -> None:
    progs = client.get("/plans/programs").json()
    assert len(progs) >= 18
    by_section: dict[str, set[str]] = {}
    for p in progs:
        assert p["level"] in ("beginner", "intermediate", "expert"), p["key"]
        assert p["section"] in SECTIONS
        by_section.setdefault(p["section"], set()).add(p["level"])
        for d in p["days"]:
            for it in d["items"]:
                assert it["exercise_id"] is not None, (
                    p["key"],
                    it["exercise"],
                )  # all in the library
    assert set(by_section) == set(SECTIONS)
    for s in ("gym", "calisthenics", "cardio", "martial_arts"):
        assert by_section[s] == {"beginner", "intermediate", "expert"}, s
    keys = {p["key"] for p in progs}
    assert {"bodyweight_starter_3", "bar_floor_starter_3"} <= keys  # day-1 programs stay


def test_generate_one_for_me_in_a_time_section(client: TestClient, profile) -> None:
    r = client.post(
        "/planner/workout", json={"section": "martial_arts", "days_per_week": 4, "use_ai": False}
    )
    assert r.status_code == 200, r.text
    draft = r.json()["draft"]
    assert len(draft["days"]) == 4 and [d["weekday"] for d in draft["days"]] == [0, 1, 3, 5]
    names = {s["exercise"] for d in draft["days"] for s in d["slots"]}
    assert "Jab-Cross Shadow Drill" in names
    saved = client.post("/planner/programs", json=draft)
    assert saved.status_code == 201, saved.text
    assert client.post(f"/planner/programs/{saved.json()['id']}/follow").status_code == 200
    plan = client.get("/plans/current").json()
    assert plan["source"] == "custom" and plan["next"]["items"][0]["measure"] == "time"


def test_generate_calisthenics_leaves_gym_kit_out(client: TestClient, profile) -> None:
    r = client.post(
        "/planner/workout",
        json={"section": "calisthenics", "days_per_week": 3, "equipment": ["gym"], "use_ai": False},
    )
    assert r.status_code == 200, r.text
    lib = {e["name"]: e for e in client.get("/exercises").json()}
    for d in r.json()["draft"]["days"]:
        for s in d["slots"]:
            assert lib[s["exercise"]]["equipment"] in ("bodyweight", "none", "mat"), s["exercise"]


def test_the_quest_follows_your_program(client: TestClient, profile, clock) -> None:
    assert (
        client.put("/plans/current", json={"program_key": "bodyweight_starter_3"}).status_code
        == 200
    )
    q = client.get("/game/summary").json()["quest"]
    item = next(i for i in q if i["code"] == "plan_session")
    assert item["title"] == "Today's session: Starter A" and item["target"] == 5
    w = client.post("/workouts").json()["id"]
    squat = next(
        e
        for e in client.get("/exercises", params={"q": "Bodyweight Squat"}).json()
        if e["name"] == "Bodyweight Squat"
    )
    client.post(
        f"/workouts/{w}/sets", json={"exercise_id": squat["id"], "weight_kg": 0, "reps": 10}
    )
    item = next(
        i for i in client.get("/game/summary").json()["quest"] if i["code"] == "plan_session"
    )
    assert item["progress"] == 1


# --- food rules (item 14) -----------------------------------------------------------------


def food_id(client: TestClient, name: str) -> int:
    return next(
        f["id"] for f in client.get("/foods", params={"q": name}).json() if f["name"] == name
    )


def test_the_food_guide_checks_todays_meals(client: TestClient) -> None:
    empty = client.get("/meals/guide").json()
    assert empty["source"] == "Dietary Guidelines for Indians, ICMR-NIN 2024"
    assert len(empty["guidelines"]) >= 8 and empty["foods_logged"] == 0
    items = [{"food_id": food_id(client, n), "portions": 1} for n in ("Idli", "Sambar", "Samosa")]
    assert client.post("/meals", json={"meal_type": "breakfast", "items": items}).status_code == 201
    g = client.get("/meals/guide").json()
    assert g["foods_logged"] == 3
    counts = {x["key"]: x["count"] for x in g["groups"]}
    assert counts["cereals_millets"] == 1 and counts["pulses"] == 1
    assert "Vegetables" in g["missing"] and g["hfss"] == ["Samosa"]
    assert 1 <= len(g["tips"]) <= 3


# --- weekly recap (item 13) ---------------------------------------------------------------


def test_the_weekly_recap_counts_the_week_and_stays_body_neutral(
    client: TestClient, profile, clock
) -> None:
    from tests.api.test_workouts import exercise_id

    clock.now -= timedelta(days=clock.now.weekday())  # Monday
    empty = client.get("/progress/recap").json()
    assert empty["sessions"] == 0 and empty["sets"] == 0 and empty["prs"] == []
    assert empty["headline"].startswith("A quiet week")
    bench = exercise_id(client, "Barbell Bench Press")
    for day, reps in ((0, 8), (2, 10)):
        w = client.post("/workouts").json()["id"]
        for _ in range(3):
            body = {"exercise_id": bench, "weight_kg": 40, "reps": reps, "rpe": 8}
            assert client.post(f"/workouts/{w}/sets", json=body).status_code == 201
        assert client.post(f"/workouts/{w}/finish").status_code == 200
        if day == 0:
            clock.now += timedelta(days=2)
    client.get("/game/boss")  # Today spawns the week's boss
    r = client.get("/progress/recap").json()
    assert r["week_start"] == (clock.now - timedelta(days=2)).date().isoformat()
    assert r["sessions"] == 2 and r["active_days"] == 2 and r["sets"] == 6
    assert r["volume_kg"] == 40 * (8 * 3 + 10 * 3)
    assert r["sections"] == [{"section": "gym", "sets": 6}]
    assert r["best_day"]["sets"] == 3 and r["xp"] > 0
    assert [p["exercise"] for p in r["prs"]] == ["Barbell Bench Press"]
    assert r["boss"] is not None and r["boss"]["tier"] in "EDCBAS"
    assert r["complete"] is False and r["rank"] == "E" and r["level"] >= 1
    assert "weight" not in r and "avg_weight_kg" not in r  # body-neutral: no body numbers
    later = client.get("/progress/recap", params={"week": r["week_end"]}).json()
    assert later["week_start"] == r["week_start"]
    nxt = (clock.now + timedelta(days=7)).date().isoformat()
    following = client.get("/progress/recap", params={"week": nxt}).json()
    assert following["sessions"] == 0 and following["last_week_sessions"] == 2
