from datetime import timedelta

from tests.api.test_workouts import exercise_id


def _session(client, clock, bench, weight):
    w = client.post("/workouts").json()
    client.post(
        f"/workouts/{w['id']}/sets",
        json={"exercise_id": bench, "weight_kg": weight, "reps": 5, "rpe": 8},
    )
    clock.now += timedelta(minutes=30)
    client.post(f"/workouts/{w['id']}/finish")
    clock.now += timedelta(days=1)
    return w["id"]


def test_list_workouts_newest_first_with_summary(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    ids = [_session(client, clock, bench, 50 + i * 5) for i in range(3)]
    items = client.get("/workouts").json()
    assert [i["id"] for i in items] == list(reversed(ids))
    newest = items[0]
    assert newest["sets"] == 1
    assert newest["volume_kg"] == 60 * 5
    assert newest["xp"] > 0
    assert newest["finished_at"] is not None


def test_list_workouts_keyset_pagination(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    ids = [_session(client, clock, bench, 40 + i) for i in range(5)]
    page1 = client.get("/workouts", params={"limit": 2}).json()
    page2 = client.get("/workouts", params={"limit": 2, "before": page1[-1]["started_at"]}).json()
    page3 = client.get("/workouts", params={"limit": 2, "before": page2[-1]["started_at"]}).json()
    seen = [i["id"] for i in page1 + page2 + page3]
    assert seen == list(reversed(ids))


def test_list_workouts_rejects_bad_limit(client):
    assert client.get("/workouts", params={"limit": 0}).status_code == 422
    assert client.get("/workouts", params={"limit": 101}).status_code == 422


def test_prs_list_best_e1rm_per_exercise(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    for ex, kg, reps in ((bench, 60, 8), (bench, 70, 5), (squat, 100, 5), (squat, 90, 5)):
        client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "weight_kg": kg, "reps": reps})
        clock.now += timedelta(minutes=3)
    prs = client.get("/prs").json()
    assert [p["exercise"] for p in prs] == ["Back Squat", "Barbell Bench Press"]
    assert prs[0]["value"] == round(100 * (1 + 5 / 30), 1)
    assert prs[1]["weight_kg"] == 70 and prs[1]["reps"] == 5
    only = client.get("/prs", params={"exercise_id": bench}).json()
    assert len(only) == 1 and only[0]["formula"] == "epley"
