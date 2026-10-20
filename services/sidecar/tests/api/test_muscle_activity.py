from datetime import timedelta

from tests.api.test_workouts import exercise_id


def _by_key(rows):
    return {r["key"]: r for r in rows}


def test_activity_sums_sets_volume_and_last_trained_per_window(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    w = client.post("/workouts").json()["id"]
    for _ in range(2):
        body = {"exercise_id": bench, "weight_kg": 100, "reps": 5, "rpe": 8}
        client.post(f"/workouts/{w}/sets", json=body)
        clock.now += timedelta(minutes=3)
    trained_at = clock.now
    clock.now += timedelta(days=3)

    week = _by_key(client.get("/muscles/activity", params={"days": 7}).json())
    assert week["lower_chest"]["sets"] == 2.0
    assert week["lower_chest"]["volume_kg"] == 1000
    # Secondary movers get their share of sets and volume.
    assert week["triceps"]["sets"] == 1.0
    assert week["triceps"]["volume_kg"] == 500
    assert week["quads"] == {"key": "quads", "sets": 0.0, "volume_kg": 0, "last_trained": None}

    # Outside the 1-day window: no sets, but "last trained" still looks back.
    day = _by_key(client.get("/muscles/activity", params={"days": 1}).json())
    assert day["lower_chest"]["sets"] == 0.0 and day["lower_chest"]["volume_kg"] == 0
    assert day["lower_chest"]["last_trained"] is not None
    assert day["lower_chest"]["last_trained"] <= trained_at.isoformat()


def test_activity_lists_every_muscle_and_validates_days(client):
    rows = client.get("/muscles/activity").json()
    muscles = client.get("/muscles").json()
    assert [r["key"] for r in rows] == [m["key"] for m in muscles]
    assert client.get("/muscles/activity", params={"days": 0}).status_code == 422
    assert client.get("/muscles/activity", params={"days": 31}).status_code == 422


def test_timed_sets_load_muscles_without_volume(client, profile):
    plank = exercise_id(client, "Plank (60 s = 1 set)")
    w = client.post("/workouts").json()["id"]
    r = client.post(
        f"/workouts/{w}/sets",
        json={"exercise_id": plank, "weight_kg": 0, "reps": 1, "duration_s": 120},
    )
    assert r.status_code == 201, r.text
    abs_row = _by_key(client.get("/muscles/activity", params={"days": 1}).json())["abs"]
    assert abs_row["sets"] > 0 and abs_row["volume_kg"] == 0
