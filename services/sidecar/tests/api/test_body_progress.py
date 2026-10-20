from datetime import timedelta


def test_log_weigh_ins_returns_trend_and_updates_profile_weight(client, profile, clock):
    r1 = client.post("/body-metrics", json={"weight_kg": 70.0, "waist_cm": 82})
    assert r1.status_code == 201
    assert r1.json()["trend_kg"] == 70.0
    clock.now += timedelta(days=1)
    r2 = client.post("/body-metrics", json={"weight_kg": 71.0, "resting_hr": 58})
    assert r2.json()["trend_kg"] == 70.1
    assert client.get("/profile").json()["weight_kg"] == 71.0
    listed = client.get("/body-metrics").json()
    assert [m["weight_kg"] for m in listed] == [70.0, 71.0]


def test_backfilled_weigh_in_does_not_overwrite_profile_weight(client, profile, clock):
    client.post("/body-metrics", json={"weight_kg": 72.0})
    old = (clock.now - timedelta(days=10)).isoformat()
    client.post("/body-metrics", json={"weight_kg": 75.0, "measured_at": old})
    assert client.get("/profile").json()["weight_kg"] == 72.0
    assert [m["weight_kg"] for m in client.get("/body-metrics").json()] == [75.0, 72.0]


def test_delete_weigh_in(client, profile):
    mid = client.post("/body-metrics", json={"weight_kg": 70.0}).json()["id"]
    assert client.delete(f"/body-metrics/{mid}").status_code == 204
    assert client.delete(f"/body-metrics/{mid}").status_code == 404
    assert client.get("/body-metrics").json() == []


def test_weigh_in_validation(client):
    assert client.post("/body-metrics", json={"weight_kg": 5}).status_code == 422


def test_measurements_report_change_per_site(client, clock):
    client.post("/measurements", json={"site": "waist", "cm": 84.0})
    client.post("/measurements", json={"site": "arm", "cm": 33.0})
    clock.now += timedelta(days=14)
    r = client.post("/measurements", json={"site": "waist", "cm": 82.5})
    assert r.json()["change_cm"] == -1.5
    waist = client.get("/measurements", params={"site": "waist"}).json()
    assert [m["cm"] for m in waist] == [84.0, 82.5]
    assert waist[0]["change_cm"] is None
    assert client.post("/measurements", json={"site": "ear", "cm": 5}).status_code == 422


def test_eta_needs_a_target_then_gives_a_range(client, profile, clock):
    assert client.get("/progress/eta").json()["reason"] == "No weigh-ins yet"
    for i in range(21):
        client.post("/body-metrics", json={"weight_kg": round(70 - 0.08 * i, 2)})
        clock.now += timedelta(days=1)
    assert client.get("/progress/eta").json()["reason"] == "Set a target weight"
    body = {**{k: profile[k] for k in ("name", "age", "sex", "height_cm", "goal", "activity")}}
    body["weight_kg"] = 68.4
    body["target_weight_kg"] = 66.0
    assert client.put("/profile", json=body).json()["target_weight_kg"] == 66.0
    eta = client.get("/progress/eta").json()
    assert eta["on_track"] is True
    assert eta["confidence"] in ("medium", "high")
    assert eta["eta_from"] < eta["eta_to"]
    assert eta["note"] == "Estimate, not a promise"


def test_weekly_summary_buckets_by_monday(client, profile, clock):
    from tests.api.test_workouts import exercise_id

    bench = exercise_id(client, "Barbell Bench Press")
    # clock starts Tue 2026-10-20; log one session this week.
    w = client.post("/workouts").json()["id"]
    client.post(
        f"/workouts/{w}/sets", json={"exercise_id": bench, "weight_kg": 60, "reps": 8, "rpe": 8}
    )
    clock.now += timedelta(minutes=40)
    client.post(f"/workouts/{w}/finish")
    client.post("/body-metrics", json={"weight_kg": 70.4})
    weeks = client.get("/progress/weekly", params={"weeks": 4}).json()
    assert len(weeks) == 4
    assert [w["week_start"] for w in weeks][-1] == "2026-10-19"
    this = weeks[-1]
    assert this["sessions"] == 1 and this["sets"] == 1
    assert this["volume_kg"] == 480.0
    assert this["active_minutes"] == 40.0
    assert this["xp"] > 0
    assert this["avg_weight_kg"] == 70.4
    assert weeks[0]["sessions"] == 0 and weeks[0]["avg_kcal_in"] is None
