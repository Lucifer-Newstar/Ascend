from datetime import timedelta

from tests.api.test_workouts import exercise_id


def _log(client, w, ex, weight, reps, rpe=8):
    r = client.post(
        f"/workouts/{w}/sets",
        json={"exercise_id": ex, "weight_kg": weight, "reps": reps, "rpe": rpe},
    )
    assert r.status_code == 201
    return r.json()["set"]


def test_fixing_a_typo_clears_the_false_pr_and_restores_the_real_one(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    w = client.post("/workouts").json()["id"]
    _log(client, w, bench, 60, 5)  # baseline
    clock.now += timedelta(minutes=3)
    typo = _log(client, w, bench, 250, 5)  # 250 kg typo for 25 -> false PR
    assert typo["is_pr"] is True
    clock.now += timedelta(minutes=3)
    real = _log(client, w, bench, 65, 5)
    assert real["is_pr"] is False  # masked by the typo

    r = client.patch(f"/workouts/{w}/sets/{typo['id']}", json={"weight_kg": 60})
    assert r.status_code == 200
    assert r.json()["is_pr"] is False
    sets = {s["id"]: s for s in client.get(f"/workouts/{w}").json()["sets"]}
    assert sets[real["id"]]["is_pr"] is True


def test_editing_rpe_rewrites_muscle_load(client, profile, clock):
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    s = _log(client, w, squat, 80, 5, rpe=6)
    before = next(m for m in client.get("/muscles").json() if m["key"] == "vastus_lateralis")
    client.patch(f"/workouts/{w}/sets/{s['id']}", json={"rpe": 9})
    after = next(m for m in client.get("/muscles").json() if m["key"] == "vastus_lateralis")
    assert after["es_7d"] > before["es_7d"]


def test_delete_set_removes_load_and_returns_204(client, profile):
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    s = _log(client, w, squat, 80, 5)
    assert client.delete(f"/workouts/{w}/sets/{s['id']}").status_code == 204
    quads = next(m for m in client.get("/muscles").json() if m["key"] == "vastus_lateralis")
    assert quads["es_7d"] == 0
    assert client.get(f"/workouts/{w}").json()["sets"] == []


def test_edit_or_delete_unknown_set_is_404(client, profile):
    w = client.post("/workouts").json()["id"]
    assert client.patch(f"/workouts/{w}/sets/999", json={"reps": 5}).status_code == 404
    assert client.delete(f"/workouts/{w}/sets/999").status_code == 404


def test_set_from_another_workout_is_404(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    w1 = client.post("/workouts").json()["id"]
    s = _log(client, w1, bench, 50, 5)
    clock.now += timedelta(minutes=40)
    client.post(f"/workouts/{w1}/finish")
    w2 = client.post("/workouts").json()["id"]
    assert client.patch(f"/workouts/{w2}/sets/{s['id']}", json={"reps": 6}).status_code == 404
