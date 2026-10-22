"""Awakening onboarding: profile focus/equipment, the baseline test and the equipment
filter on quest and skill suggestions."""

import pytest

from app.modules.workouts.equipment import allowed_equipment, fits

BASE = {
    "name": "",
    "age": 21,
    "sex": "male",
    "height_cm": 175,
    "weight_kg": 70,
    "goal": "maintain",
    "activity": "moderate",
}


def test_profile_round_trips_focus_and_equipment(client):
    r = client.put(
        "/profile", json={**BASE, "focus": "skills", "equipment": ["rings", "pullup_bar", "rings"]}
    )
    assert r.status_code == 200, r.text
    p = client.get("/profile").json()
    assert p["focus"] == "skills"
    assert p["equipment"] == ["pullup_bar", "rings"]  # sorted, no duplicates
    assert p["baseline"] is None


def test_old_clients_keep_working_without_the_new_fields(client):
    assert client.put("/profile", json=BASE).status_code == 200
    p = client.get("/profile").json()
    assert p["equipment"] == [] and p["focus"] is None


def test_unknown_equipment_is_rejected(client):
    assert client.put("/profile", json={**BASE, "equipment": ["laser"]}).status_code == 422


def test_baseline_logs_max_sets_in_one_finished_session_and_is_kept(client):
    client.put("/profile", json={**BASE, "equipment": ["pullup_bar"]})
    r = client.post(
        "/profile/baseline",
        json={"pushups": 22, "pullups": 0, "dead_hang_s": 40, "plank_s": 75, "bodyweight_kg": 71.2},
    )
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["sets_logged"] == 3  # 0 pull-ups is "not done", squats skipped
    assert out["xp_awarded"] > 0
    assert out["rank"] in "EDCBAS" and out["level"] >= 1
    w = client.get(f"/workouts/{out['workout_id']}").json()
    assert w["finished_at"] is not None
    got = sorted((s["exercise_name"], s["reps"], s["duration_s"], s["rpe"]) for s in w["sets"])
    assert got == [
        ("Dead Hang", 1, 40, 10.0),
        ("Plank", 1, 75, 10.0),
        ("Push-up", 22, None, 10.0),
    ]
    p = client.get("/profile").json()
    assert p["baseline"]["pushups"] == 22 and p["baseline"]["taken_at"]
    assert p["weight_kg"] == 71.2
    assert client.get("/workouts/active").json() is None


def test_baseline_needs_a_profile_and_at_least_one_result(client):
    assert client.post("/profile/baseline", json={"pushups": 10}).status_code == 409
    client.put("/profile", json=BASE)
    assert client.post("/profile/baseline", json={}).status_code == 422
    assert client.post("/profile/baseline", json={"pushups": 0}).status_code == 422
    assert client.post("/profile/baseline", json={"pushups": 500}).status_code == 422


def test_equipment_filter_rules():
    assert allowed_equipment([]) is None
    assert allowed_equipment(["gym", "none"]) is None
    dumbbells = allowed_equipment(["dumbbells"])
    assert fits("dumbbell", dumbbells) and fits("bodyweight", dumbbells)
    assert not fits("barbell", dumbbells) and not fits("bar", dumbbells)
    assert fits("bar", allowed_equipment(["pullup_bar"]))
    assert fits("barbell", None)


@pytest.mark.parametrize("day_offset", range(14))
def test_dumbbell_only_user_never_gets_a_barbell_quest_item(client, clock, day_offset):
    from datetime import timedelta

    client.put("/profile", json={**BASE, "equipment": ["dumbbells"]})
    clock.now += timedelta(days=day_offset)
    lib = {e["name"]: e["equipment"] for e in client.get("/exercises").json()}
    quest = client.get("/game/summary").json()["quest"]
    for item in quest:
        if item["kind"] != "training" or "Suggested:" not in item["detail"]:
            continue
        name = item["detail"].split("Suggested: ", 1)[1].split(". Any", 1)[0]
        assert lib[name] in {"dumbbell", "bodyweight", "none", "mat"}, (name, lib[name])


def test_skill_training_skips_exercises_the_user_cannot_do(client):
    client.put("/profile", json={**BASE, "equipment": ["none"]})
    r = client.post("/skills/front_lever/train").json()
    lib = {e["id"]: e["equipment"] for e in client.get("/exercises").json()}
    quest = client.get("/game/summary").json()["quest"]
    skill_items = [q for q in quest if q["code"].startswith("skill:")]
    for item in skill_items:
        ex_id = int(item["code"].split(":")[2])
        assert lib[ex_id] in {"bodyweight", "none", "mat"}, item["title"]
    assert r["added"] == len(skill_items)
    if not r["added"]:
        assert "fit the equipment" in r["message"]
