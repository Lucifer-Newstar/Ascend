"""Planner: draft, edit, save and follow a custom program; draft and save a meal plan."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.planner import workout_gen


def test_every_generator_exercise_is_in_the_library(client: TestClient) -> None:
    names = {e["name"] for e in client.get("/exercises").json()}
    missing = {
        c for slot in workout_gen.SLOTS.values() for tier in slot.values() for c in tier
    } - names
    assert missing == set()


def test_check_flags_an_unrealistic_goal(client: TestClient) -> None:
    r = client.post("/planner/check", json={"weight_kg": 80, "target_weight_kg": 70, "weeks": 4})
    body = r.json()
    assert body["worst"] == "block"
    assert body["flags"][0]["code"] == "loss_too_fast"


def test_draft_follows_equipment_and_schedule(client: TestClient, profile: dict) -> None:
    r = client.post(
        "/planner/workout",
        json={"focus": "muscle", "days_per_week": 4, "minutes": 60, "equipment": ["dumbbells"]},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    draft = out["draft"]
    assert out["phrased_by"] == "rules"  # Ollama is unreachable in tests
    assert [d["name"] for d in draft["days"]] == ["Upper 1", "Lower 1", "Upper 2", "Lower 2"]
    exercises = {s["exercise"] for d in draft["days"] for s in d["slots"]}
    assert "Barbell Bench Press" not in exercises and "Back Squat" not in exercises
    assert all(len(d["slots"]) == 6 for d in draft["days"])  # 60 min -> 6 exercises
    assert all(s["exercise_id"] for d in draft["days"] for s in d["slots"])


def test_seven_days_is_flagged_and_capped(client: TestClient, profile: dict) -> None:
    out = client.post("/planner/workout", json={"days_per_week": 7}).json()
    assert len(out["draft"]["days"]) == 6
    assert "no_rest_day" in [f["code"] for f in out["flags"]]


def test_save_edit_follow_and_delete(client: TestClient, profile: dict) -> None:
    draft = client.post("/planner/workout", json={"days_per_week": 3, "minutes": 45}).json()[
        "draft"
    ]
    draft["name"] = "My plan"
    draft["days"][0]["slots"][0]["sets"] = 5
    saved = client.post("/planner/programs", json=draft)
    assert saved.status_code == 201, saved.text
    pid = saved.json()["id"]
    assert saved.json()["key"] == f"custom-{pid}"

    bad = dict(
        draft,
        days=[
            dict(
                draft["days"][0], slots=[{**draft["days"][0]["slots"][0], "exercise": "Moon Squat"}]
            )
        ],
    )
    assert client.put(f"/planner/programs/{pid}", json=bad).status_code == 422

    followed = client.post(f"/planner/programs/{pid}/follow").json()
    assert followed["following"] is True
    plan = client.get("/plans/current").json()
    assert plan["program_key"] == f"custom-{pid}" and plan["source"] == "custom"
    assert plan["next"]["items"][0]["sets"] == 5

    assert client.delete(f"/planner/programs/{pid}").status_code == 204
    assert client.get("/planner/programs").json() == []
    assert client.get("/plans/current").json() is None


def test_diet_draft_meets_targets_and_respects_veg(client: TestClient, profile: dict) -> None:
    r = client.post("/planner/diet", json={"diet": "veg"})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert len(plan["days"]) == 7
    foods = {i["food"] for d in plan["days"] for m in d["meals"] for i in m["items"]}
    assert not foods & {"Chicken curry", "Fish curry", "Chicken biryani", "Boiled egg"}
    for d in plan["days"]:  # within 15 % of the engine's calorie target
        assert abs(d["kcal"] - plan["kcal_target"]) / plan["kcal_target"] < 0.15
    saved = client.post("/planner/diets", json={"name": "Veg week", "plan": plan})
    assert saved.status_code == 201
    assert client.get("/planner/diets").json()[0]["active"] is True


def test_diet_below_floor_is_raised_to_the_floor(client: TestClient, profile: dict) -> None:
    plan = client.post("/planner/diet", json={"kcal_target": 900}).json()
    assert plan["flags"][0]["code"] == "kcal_below_floor"
    assert plan["kcal_target"] >= 1500


def test_diet_needs_a_profile(client: TestClient) -> None:
    assert client.post("/planner/diet", json={}).status_code == 409


def test_under_18_gets_no_deficit_plan(client) -> None:
    client.put(
        "/profile",
        json={"name": "Arun", "age": 16, "sex": "male", "height_cm": 170, "weight_kg": 70,
              "goal": "cut", "activity": "moderate"},
    )  # fmt: skip
    r = client.post("/planner/diet", json={}).json()
    codes = [f["code"] for f in r["flags"]]
    assert "under_18_no_deficit" in codes
    tdee = client.get("/profile").json()["energy"]["tdee"]
    assert abs(r["kcal_target"] - tdee) <= 1
    chk = client.post(
        "/planner/check", json={"weight_kg": 70, "target_weight_kg": 66, "weeks": 10, "age": 16}
    ).json()
    assert chk["worst"] == "block"
