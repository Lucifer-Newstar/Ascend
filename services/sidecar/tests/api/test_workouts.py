from datetime import timedelta


def exercise_id(client, name):
    return next(
        e["id"] for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name
    )


def test_exercise_search_returns_muscle_weights(client):
    squat = client.get("/exercises", params={"q": "back squat"}).json()[0]
    assert squat["muscles"][0]["weight"] == 1.0
    assert {m["muscle"] for m in squat["muscles"]} >= {"quads", "glutes"}


def test_log_sets_awards_xp_and_detects_pr(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    w = client.post("/workouts").json()
    first = client.post(
        f"/workouts/{w['id']}/sets",
        json={"exercise_id": bench, "weight_kg": 60, "reps": 8, "rpe": 8},
    )
    assert first.status_code == 201
    assert first.json()["set"]["is_pr"] is False  # baseline
    assert first.json()["xp_awarded"] == 3

    clock.now += timedelta(minutes=3)
    second = client.post(
        f"/workouts/{w['id']}/sets",
        json={"exercise_id": bench, "weight_kg": 70, "reps": 8, "rpe": 9},
    ).json()
    assert second["set"]["is_pr"] is True
    assert second["set"]["e1rm"] == 88.7
    assert second["xp_awarded"] == 3 + 40
    assert second["previous_best_e1rm"] == 76.0


def test_finish_awards_session_xp_and_updates_muscles(client, profile, clock):
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()
    for _ in range(4):
        client.post(
            f"/workouts/{w['id']}/sets",
            json={"exercise_id": squat, "weight_kg": 80, "reps": 6, "rpe": 8},
        )
    clock.now += timedelta(minutes=40)
    r = client.post(f"/workouts/{w['id']}/finish")
    assert r.status_code == 200
    assert r.json()["hard_sets"] == 4
    # 20 base + 0.5 x 40 min = 40, x 1.02 streak bonus (today is now an active day) = 41
    assert r.json()["xp_awarded"] == 41
    quads = next(m for m in client.get("/muscles").json() if m["key"] == "quads")
    assert quads["es_7d"] == 4.0
    assert quads["status"] == "recovering"


def test_cannot_finish_empty_or_twice(client, profile):
    w = client.post("/workouts").json()
    assert client.post(f"/workouts/{w['id']}/finish").status_code == 409


def test_unknown_exercise_404(client, profile):
    w = client.post("/workouts").json()
    r = client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": 9999, "weight_kg": 10, "reps": 5}
    )
    assert r.status_code == 404


def test_start_returns_existing_active_workout(client, profile):
    a = client.post("/workouts").json()
    b = client.post("/workouts").json()
    assert a["id"] == b["id"]
