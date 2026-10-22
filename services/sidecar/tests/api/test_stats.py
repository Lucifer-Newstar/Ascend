"""GET /game/stats: five computed stats with their inputs."""


def test_stats_endpoint_returns_five_scores_with_inputs(client, profile):
    r = client.get("/game/stats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == "stats-v1" and body["window_days"] == 28
    assert [s["key"] for s in body["stats"]] == ["str", "agi", "end", "vit", "int"]
    strength = body["stats"][0]
    assert strength["inputs"]["bodyweight_kg"] == 70
    assert all(s["value"] == 0 for s in body["stats"]), body


def test_a_logged_cardio_session_raises_endurance(client, profile):
    run = next(
        e for e in client.get("/exercises", params={"q": "Running"}).json() if e["time_based"]
    )
    w = client.post("/workouts", params={"section": "cardio"}).json()["id"]
    r = client.post(f"/workouts/{w}/sets", json={"exercise_id": run["id"], "duration_s": 60 * 60})
    assert r.status_code == 201, r.text
    end = next(s for s in client.get("/game/stats").json()["stats"] if s["key"] == "end")
    assert end["inputs"]["cardio_minutes"] == 60 and end["value"] == 10
