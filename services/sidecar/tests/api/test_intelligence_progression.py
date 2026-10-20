"""prog-v1 over HTTP: targets, "keep mine", stalls, the deload week and skill targets."""

from datetime import timedelta

from tests.api.test_workouts import exercise_id


def session(client, clock, ex, sets, days_later=3.0):
    """One finished workout of `sets` [(weight, reps, rpe)], then move the clock on."""
    w = client.post("/workouts").json()["id"]
    for weight, reps, rpe in sets:
        r = client.post(
            f"/workouts/{w}/sets",
            json={"exercise_id": ex, "weight_kg": weight, "reps": reps, "rpe": rpe},
        )
        assert r.status_code == 201, r.text
    clock.now += timedelta(minutes=40)
    client.post(f"/workouts/{w}/finish")
    clock.now += timedelta(days=days_later)


def test_first_time_then_double_progression(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    first = client.get(f"/intelligence/progression/{bench}").json()
    assert first["change"] == "first" and first["algo_version"] == "prog-v1"
    session(client, clock, bench, [(60, 10, 8)] * 3)
    t = client.get(f"/intelligence/progression/{bench}").json()
    assert (t["change"], t["reason"]) == ("up_load", "top_of_range")
    assert (t["weight_kg"], t["reps"], t["sets"]) == (62.5, 6, 3)
    assert t["explanation"]["inputs"]["last_sets"] == "10, 10, 10"
    assert t["e1rm"]["unit"] == "kg" and t["e1rm"]["last"] == round(60 * (1 + 12 / 30), 1)
    assert "+2.5 kg" in t["why"] and t["phrasing"] == "template"


def test_keep_mine_holds_for_seven_days(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 10, 8)] * 3)
    d = client.post(f"/intelligence/progression/{bench}/decision", json={"choice": "kept"})
    assert d.status_code == 201 and d.json()["kept_until"] is not None
    t = client.get(f"/intelligence/progression/{bench}").json()
    assert t["reason"] == "kept" and t["weight_kg"] == 60 and t["kept_until"]
    clock.now += timedelta(days=8)
    assert client.get(f"/intelligence/progression/{bench}").json()["reason"] == "top_of_range"
    bad = client.post(f"/intelligence/progression/{bench}/decision", json={"choice": "maybe"})
    assert bad.status_code == 422


def test_fatigued_muscles_hold_the_increase(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 10, 8)] * 10, days_later=0.05)
    t = client.get(f"/intelligence/progression/{bench}").json()
    assert t["reason"] == "hold_recovering" and t["weight_kg"] == 60
    assert t["readiness"] is not None and t["readiness"] < 0.4


def test_stalled_lift_resets_and_is_listed(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    for _ in range(4):
        session(client, clock, bench, [(80, 8, 9)] * 3)
    t = client.get(f"/intelligence/progression/{bench}").json()
    assert t["stalled"] and t["reason"] == "stall_reset" and t["weight_kg"] == 71.25
    stalls = client.get("/intelligence/stalls").json()
    assert [s["exercise"] for s in stalls] == ["Barbell Bench Press"]
    assert stalls[0]["unit"] == "kg" and stalls[0]["sessions_flat"] == 3
    signal = next(
        s for s in client.get("/deload").json()["signals"] if s["code"] == "STALLED_LIFTS"
    )
    assert signal["active"] is False  # one stalled lift is not the signal (2 needed)


def test_deload_week_halves_the_sets(client, profile, clock):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 8, 8)] * 4)
    assert client.post("/deload/start").status_code in (200, 201)
    t = client.get(f"/intelligence/progression/{bench}").json()
    assert (t["reason"], t["sets"], t["rpe"], t["deload_week"]) == ("deload_week", 2, 7.0, True)


def test_calisthenics_targets_follow_the_skill_tree(client, profile, clock):
    ex = exercise_id(client, "Scapular Pull-up")
    session(client, clock, ex, [(0, 7, None)] * 3)
    t = client.get(f"/intelligence/progression/{ex}").json()
    assert t["skill"]["criterion"] == "3\u00d710"
    assert t["skill"]["step_name"] == "Negative pull-up"
    assert t["reps"] == 8 and t["e1rm"]["unit"] == "reps"


def test_unknown_exercise_is_404(client):
    assert client.get("/intelligence/progression/999999").status_code == 404
