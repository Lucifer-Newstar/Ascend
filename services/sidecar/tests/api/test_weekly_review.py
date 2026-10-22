from datetime import timedelta

from tests.api.test_workouts import exercise_id


def test_new_user_gets_an_empty_review(client, profile):
    r = client.get("/coach/weekly-review/latest").json()
    assert r["findings"] == [] and r["top"] == []
    assert r["summary"].startswith("This week: 0 of 3 planned sessions done.")
    assert r["summary_source"] == "template" and r["algo_version"] == "review-v1"


def _session(client, clock, ex, sets, kg=60):
    w = client.post("/workouts").json()["id"]
    for _ in range(sets):
        client.post(
            f"/workouts/{w}/sets", json={"exercise_id": ex, "weight_kg": kg, "reps": 5, "rpe": 8}
        )
        clock.now += timedelta(minutes=3)
    clock.now += timedelta(minutes=30)
    client.post(f"/workouts/{w}/finish")


def test_low_adherence_and_under_muscle_are_found_and_ranked(client, profile, clock):
    curl = exercise_id(client, "Barbell Curl")
    # Week 1 (3 weeks ago): normal training, establishes history.
    clock.now -= timedelta(days=21)
    for _ in range(3):
        _session(client, clock, curl, 2)
        clock.now += timedelta(days=2)
    # Last two weeks: one short session each.
    clock.now += timedelta(days=1)
    _session(client, clock, curl, 2)
    clock.now += timedelta(days=7)
    _session(client, clock, curl, 2)
    clock.now += timedelta(days=3)
    r = client.get("/coach/weekly-review/latest").json()
    codes = [f["code"] for f in r["findings"]]
    assert codes[0] == "ADHERENCE_LOW"
    assert "MUSCLE_UNDER" in codes
    under = next(f for f in r["findings"] if f["code"] == "MUSCLE_UNDER")
    assert under["numbers"]["muscle"] == "biceps_long"
    assert len(r["top"]) <= 3
    # Every number in the summary appears in a finding or the session count.
    assert "1 of 3" in r["findings"][0]["detail"]
    assert r["summary"].startswith("This week: 1 of 3 planned sessions done. Main finding:")


def test_protein_low_on_most_logged_days(client, profile, clock):
    idli = next(f for f in client.get("/foods", params={"q": "idli"}).json())
    for _ in range(5):
        client.post(
            "/meals",
            json={"meal_type": "breakfast", "items": [{"food_id": idli["id"], "portions": 1}]},
        )
        clock.now += timedelta(days=1)
    r = client.get("/coach/weekly-review/latest").json()
    protein = next(f for f in r["findings"] if f["code"] == "PROTEIN_LOW")
    assert protein["numbers"]["days_low"] == 5
    assert protein["proposal"] is None


def test_flat_weight_on_a_bulk_is_a_stall(client, profile, clock):
    clock.now -= timedelta(days=13)
    for i in range(14):
        client.post("/body-metrics", json={"weight_kg": 70.0 + (0.1 if i % 2 else -0.1)})
        clock.now += timedelta(days=1)
    clock.now -= timedelta(hours=1)
    r = client.get("/coach/weekly-review/latest").json()
    stall = next(f for f in r["findings"] if f["code"] == "WEIGHT_STALL")
    assert "+150" in stall["proposal"]
    assert abs(stall["numbers"]["rate_kg_per_week"]) < 0.1
