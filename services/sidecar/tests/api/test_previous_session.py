"""GET /exercises/{id}/previous: the logger's grey "last time" values."""


def ex(client, name):
    return next(e for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name)


def session(client, exercise_id, sets, finish=True):
    w = client.post("/workouts").json()["id"]
    for body in sets:
        r = client.post(f"/workouts/{w}/sets", json={"exercise_id": exercise_id, **body})
        assert r.status_code == 201, r.text
    if finish:
        assert client.post(f"/workouts/{w}/finish").status_code == 200
    return w


def test_never_logged_is_null_and_unknown_exercise_is_404(client, profile):
    bench = ex(client, "Barbell Bench Press")
    assert client.get(f"/exercises/{bench['id']}/previous").json() is None
    assert client.get("/exercises/999999/previous").status_code == 404


def test_returns_the_last_finished_session_in_order_and_skips_the_active_one(
    client, clock, profile
):
    from datetime import timedelta

    bench = ex(client, "Barbell Bench Press")
    session(client, bench["id"], [{"weight_kg": 50, "reps": 8}])
    clock.now += timedelta(days=2)
    w2 = session(
        client, bench["id"], [{"weight_kg": 60, "reps": 8, "rpe": 8}, {"weight_kg": 60, "reps": 7}]
    )
    clock.now += timedelta(days=2)
    # Today's session is still open: its sets must not become "last time".
    session(client, bench["id"], [{"weight_kg": 62.5, "reps": 8}], finish=False)
    prev = client.get(f"/exercises/{bench['id']}/previous").json()
    assert prev["workout_id"] == w2
    assert [(s["weight_kg"], s["reps"], s["rpe"]) for s in prev["sets"]] == [
        (60, 8, 8),
        (60, 7, None),
    ]


def test_holds_keep_their_seconds(client, profile):
    plank = ex(client, "Plank")
    session(client, plank["id"], [{"duration_s": 45}, {"duration_s": 40}])
    prev = client.get(f"/exercises/{plank['id']}/previous").json()
    assert [s["duration_s"] for s in prev["sets"]] == [45, 40]
    assert prev["sets"][0]["measure"] == "hold"
