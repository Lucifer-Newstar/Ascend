from datetime import timedelta

from tests.api.test_workouts import exercise_id


def test_drilldown_lists_daily_load_contributing_sets_and_suggestion(client, profile, clock):
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    for _ in range(3):
        client.post(
            f"/workouts/{w}/sets", json={"exercise_id": squat, "weight_kg": 80, "reps": 5, "rpe": 8}
        )
        clock.now += timedelta(minutes=3)
    clock.now += timedelta(days=2)
    h = client.get("/muscles/quads/history", params={"days": 7}).json()
    assert h["code"] == "quads" and h["days"] == 7
    assert len(h["daily"]) == 7
    loaded = [d for d in h["daily"] if d["eff_sets"] > 0]
    assert len(loaded) == 1 and loaded[0]["eff_sets"] == 3.0
    # Readiness dips on the training day and recovers afterwards.
    idx = h["daily"].index(loaded[0])
    assert h["daily"][idx]["readiness"] < h["daily"][-1]["readiness"]
    assert len(h["contributing_sets"]) == 3
    assert h["contributing_sets"][0]["exercise"] == "Back Squat"
    assert h["contributing_sets"][0]["weight"] == 1.0
    assert h["status"] == "under"
    assert "more hard sets" in h["suggestion"]


def test_drilldown_month_window_and_validation(client):
    month = client.get("/muscles/lats/history", params={"days": 30}).json()
    assert len(month["daily"]) == 30
    assert month["status"] == "no_data"
    assert client.get("/muscles/wings/history").status_code == 404
    assert client.get("/muscles/lats/history", params={"days": 31}).status_code == 422
