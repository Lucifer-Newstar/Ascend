from datetime import timedelta

GOOD = {"sleep": 5, "energy": 4, "soreness": "none", "mood": 4}
MEH = {"sleep": 3, "energy": 3, "soreness": "some", "mood": 3}
BAD = {"sleep": 1, "energy": 2, "soreness": "a_lot", "mood": 2}


def training_item(client):
    return next(q for q in client.get("/game/summary").json()["quest"] if q["kind"] == "training")


def test_checkin_scores_and_is_one_per_day(client, profile):
    r = client.post("/checkins", json=GOOD)
    assert r.status_code == 201
    body = r.json()
    assert body["band"] == "green" and body["readiness"] >= 70
    assert body["algo_version"] == "readiness-v1"
    again = client.post("/checkins", json=BAD).json()
    assert again["band"] == "red"
    assert client.get("/checkins/today").json()["band"] == "red"
    assert len(client.get("/checkins").json()) == 1


def test_amber_cuts_one_set_and_red_swaps_for_mobility(client, profile):
    base = training_item(client)
    assert base["metric"].startswith("sets:")
    client.post("/checkins", json=MEH)
    amber = training_item(client)
    assert amber["target"] == base["target"] - 1
    assert "One set shorter" in amber["detail"]
    client.post("/checkins", json=BAD)
    red = training_item(client)
    assert red["code"] == "mobility_15"
    client.post("/checkins", json=GOOD)  # feeling better after all
    assert training_item(client)["target"] == base["target"]


def test_checkin_after_training_started_leaves_quest_alone(client, profile, clock):
    item = training_item(client)
    muscle = item["metric"].split(":", 1)[1]
    ex = next(
        e
        for e in client.get("/exercises").json()
        if any(m["muscle"] == muscle and m["weight"] >= 1.0 for m in e["muscles"])
        and e["measure"] == "reps"
    )
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": ex["id"], "weight_kg": 20, "reps": 8})
    clock.now += timedelta(minutes=5)
    body = client.post("/checkins", json=BAD).json()
    assert training_item(client)["code"] == item["code"]
    assert body["band"] == "red"
    assert "already under way" in body["quest_adjustment"]
    assert "already under way" in client.get("/checkins/today").json()["quest_adjustment"]


def test_note_matches_what_happened_before_training(client, profile):
    body = client.post("/checkins", json=BAD).json()
    assert body["quest_adjustment"].startswith("Today's training quest is swapped")
    good = client.post("/checkins", json=GOOD).json()
    assert good["quest_adjustment"] == "Today's plan is unchanged."


def test_skipped_checkin_and_history(client, profile, clock):
    assert client.get("/checkins/today").json() is None
    client.post("/checkins", json=GOOD)
    clock.now += timedelta(days=1)
    client.post("/checkins", json=MEH)
    days = client.get("/checkins", params={"days": 7}).json()
    assert [d["band"] for d in days] == ["green", "amber"]


def test_checkin_validation(client):
    assert client.post("/checkins", json={**GOOD, "sleep": 6}).status_code == 422
    assert client.post("/checkins", json={**GOOD, "soreness": "extreme"}).status_code == 422
