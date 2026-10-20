from datetime import timedelta


def ex(client, name):
    return next(e for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name)


def test_log_a_run_with_duration_and_distance(client, profile, clock):
    run = ex(client, "Running")
    w = client.post("/workouts", params={"section": "cardio"}).json()
    assert w["section"] == "cardio"
    r = client.post(
        f"/workouts/{w['id']}/sets",
        json={
            "exercise_id": run["id"],
            "duration_s": 1800,
            "distance_m": 5000,
            "avg_hr": 152,
            "rpe": 7,
        },
    )
    assert r.status_code == 201
    s = r.json()["set"]
    assert (s["duration_s"], s["distance_m"], s["avg_hr"]) == (1800, 5000, 152)
    assert s["e1rm"] is None and s["is_pr"] is False


def test_time_based_set_without_duration_is_422(client, profile):
    bag = ex(client, "Heavy Bag Rounds")
    w = client.post("/workouts").json()
    r = client.post(f"/workouts/{w['id']}/sets", json={"exercise_id": bag["id"], "reps": 3})
    assert r.status_code == 422
    assert "duration_s" in r.json()["detail"]


def test_session_takes_the_section_of_its_first_set(client, profile, clock):
    hold = ex(client, "Pigeon Pose")
    w = client.post("/workouts").json()  # started from Gym
    assert w["section"] == "gym"
    client.post(f"/workouts/{w['id']}/sets", json={"exercise_id": hold["id"], "duration_s": 60})
    assert client.get(f"/workouts/{w['id']}").json()["section"] == "flexibility"
    clock.now += timedelta(minutes=10)
    finished = client.post(f"/workouts/{w['id']}/finish").json()
    assert finished["workout"]["section"] == "flexibility"
    assert client.get("/workouts").json()[0]["section"] == "flexibility"


def test_unknown_section_on_start_is_422(client):
    assert client.post("/workouts", params={"section": "dance"}).status_code == 422


def test_edit_duration_of_a_logged_round(client, profile):
    pads = ex(client, "Muay Thai Pad Work")
    w = client.post("/workouts").json()
    s = client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": pads["id"], "duration_s": 180}
    ).json()["set"]
    r = client.patch(f"/workouts/{w['id']}/sets/{s['id']}", json={"duration_s": 240})
    assert r.status_code == 200
    assert r.json()["duration_s"] == 240


def test_run_loads_calves_and_stretch_loads_nothing(client, profile):
    run = ex(client, "Running")
    stretch = ex(client, "Standing Hamstring Stretch")
    w = client.post("/workouts").json()
    client.post(f"/workouts/{w['id']}/sets", json={"exercise_id": stretch["id"], "duration_s": 90})
    hams = next(m for m in client.get("/muscles").json() if m["key"] == "hamstrings")
    assert hams["es_7d"] == 0
    client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": run["id"], "duration_s": 1800, "rpe": 7}
    )
    calves = next(m for m in client.get("/muscles").json() if m["key"] == "calves")
    assert calves["es_7d"] == 3.0  # weight 1.0 x min(3, 30/10) x effort 1.0
