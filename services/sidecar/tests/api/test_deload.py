from datetime import timedelta

from tests.api.test_workouts import exercise_id


def _week_of_sessions(client, clock, ex, sessions):
    start = clock.now
    for _ in range(sessions):
        w = client.post("/workouts").json()["id"]
        client.post(
            f"/workouts/{w}/sets", json={"exercise_id": ex, "weight_kg": 60, "reps": 5, "rpe": 7}
        )
        clock.now += timedelta(minutes=45)
        client.post(f"/workouts/{w}/finish")
        clock.now += timedelta(days=2)
    clock.now = start + timedelta(days=7)


def test_no_deload_for_a_new_user(client, profile):
    d = client.get("/deload").json()
    assert d["recommended"] is False and d["kind"] == "none"
    assert len(d["signals"]) == 5 and not any(s["active"] for s in d["signals"])
    assert d["algo_version"] == "deload-v2"


def test_planned_deload_after_three_training_weeks_then_accept(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    clock.now -= timedelta(days=clock.now.weekday())  # Monday
    for _ in range(3):
        _week_of_sessions(client, clock, bench, 3)
    d = client.get("/deload").json()
    assert (d["recommended"], d["kind"], d["training_weeks"]) == (True, "planned", 3)
    accepted = client.post("/deload/start").json()
    assert accepted["kind"] == "active" and accepted["recommended"] is False
    assert accepted["deload_week"] == clock.now.date().isoformat()
    # The week after the deload starts a new block.
    clock.now += timedelta(days=7)
    assert client.get("/deload").json()["kind"] == "none"


def test_reactive_deload_from_checkins(client, profile, clock):
    bad = {"sleep": 1, "energy": 2, "soreness": "a_lot", "mood": 2}
    for _ in range(3):
        client.post("/checkins", json=bad)
        clock.now += timedelta(days=1)
    d = client.get("/deload").json()
    active = {s["code"] for s in d["signals"] if s["active"]}
    assert active == {"LOW_READINESS", "HEAVY_SORENESS"}
    assert (d["recommended"], d["kind"]) == (True, "reactive")


def test_fatigue_buildup_counts_regions_not_heads(client, profile, clock):
    # One heavy squat day tires four quadriceps heads, glutes and adductors: that is a few
    # v7 regions, not a dozen strained "muscles" (taxonomy v2, ADR-0021).
    squat = exercise_id(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    for _ in range(10):
        client.post(
            f"/workouts/{w}/sets",
            json={"exercise_id": squat, "weight_kg": 100, "reps": 5, "rpe": 9},
        )
    clock.now += timedelta(hours=2)
    buildup = next(
        s for s in client.get("/deload").json()["signals"] if s["code"] == "FATIGUE_BUILDUP"
    )
    strained = int(buildup["detail"].split()[0])
    assert 1 <= strained <= 5
