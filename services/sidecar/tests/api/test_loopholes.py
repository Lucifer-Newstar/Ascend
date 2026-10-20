"""Loopholes found in the ASCEND v4 sweep, one test per finding.

See docs/operations/loophole-sweep.md for the table of findings and fixes.
"""

from datetime import datetime, timedelta

from app.modules.gamification import formulas as f


def ex(client, name):
    return next(
        e["id"] for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name
    )


def xp(client):
    return client.get("/game/summary").json()["xp"]["total"]


def log(client, w, exercise_id, **kw):
    r = client.post(f"/workouts/{w}/sets", json={"exercise_id": exercise_id, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_delete_then_relog_does_not_pay_twice(client, profile):
    bench = ex(client, "Barbell Bench Press")
    w = client.post("/workouts").json()["id"]
    start = xp(client)
    s = log(client, w, bench, weight_kg=60, reps=8, rpe=8)
    assert xp(client) == start + 3
    client.delete(f"/workouts/{w}/sets/{s['set']['id']}")
    assert xp(client) == start  # reversed
    log(client, w, bench, weight_kg=60, reps=8, rpe=8)
    assert xp(client) == start + 3


def test_pr_xp_rules_typo_jump_once_per_day_and_edits(client, profile, clock):
    bench = ex(client, "Barbell Bench Press")
    w = client.post("/workouts").json()["id"]
    log(client, w, bench, weight_kg=60, reps=5)
    client.post(f"/workouts/{w}/finish")
    clock.now += timedelta(days=1)
    w = client.post("/workouts").json()["id"]
    typo = log(client, w, bench, weight_kg=600 / 1.2, reps=5)  # 500 kg: a typo, not a PR to pay
    assert typo["set"]["is_pr"] and typo["xp_awarded"] == 3
    client.delete(f"/workouts/{w}/sets/{typo['set']['id']}")
    first = log(client, w, bench, weight_kg=62.5, reps=5)
    assert first["set"]["is_pr"] and first["xp_awarded"] == 3 + f.PR_XP
    second = log(client, w, bench, weight_kg=65, reps=5)
    assert (
        second["set"]["is_pr"] and second["xp_awarded"] == 3
    )  # one PR payout per exercise per day
    before = xp(client)
    # Editing the paid PR below the old best takes its PR XP back...
    client.patch(f"/workouts/{w}/sets/{first['set']['id']}", json={"weight_kg": 50})
    assert xp(client) == before - f.PR_XP
    # ...and editing it back up does not pay again.
    client.patch(f"/workouts/{w}/sets/{first['set']['id']}", json={"weight_kg": 62.5})
    assert xp(client) == before - f.PR_XP


def test_set_xp_has_diminishing_returns(client, profile):
    curl = ex(client, "Dumbbell Curl")
    w = client.post("/workouts").json()["id"]
    paid = [log(client, w, curl, weight_kg=10, reps=10, rpe=8)["xp_awarded"] for _ in range(12)]
    assert paid[:10] == [3] * 10 and paid[10:] == [0, 0]


def test_session_bonus_needs_real_work_and_caps_idle_minutes(client, profile, clock):
    squat = ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    log(client, w, squat, weight_kg=60, reps=5)
    clock.now += timedelta(minutes=30)
    assert client.post(f"/workouts/{w}/finish").json()["xp_awarded"] == 0  # 1-set "session"
    w = client.post("/workouts").json()["id"]
    for _ in range(3):
        log(client, w, squat, weight_kg=60, reps=5)
    clock.now += timedelta(hours=3)  # left open all afternoon
    bonus = client.post(f"/workouts/{w}/finish").json()["xp_awarded"]
    assert bonus <= round((f.SESSION_BASE_XP + 0.5 * 30) * f.STREAK_BONUS_MAX)
    for _ in range(2):  # a third and fourth paid session the same day get nothing
        w = client.post("/workouts").json()["id"]
        for _ in range(3):
            log(client, w, squat, weight_kg=60, reps=5)
        last = client.post(f"/workouts/{w}/finish").json()["xp_awarded"]
    assert last == 0


def test_deleting_sets_from_a_finished_session_reverses_its_bonus(client, profile, clock):
    squat = ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    sets = [log(client, w, squat, weight_kg=60, reps=5) for _ in range(3)]
    clock.now += timedelta(minutes=20)
    bonus = client.post(f"/workouts/{w}/finish").json()["xp_awarded"]
    assert bonus > 0
    before = xp(client)
    client.delete(f"/workouts/{w}/sets/{sets[0]['set']['id']}")
    assert xp(client) == before - 3 - bonus


def test_sets_after_midnight_count_for_the_new_day(client, profile, clock):
    clock.now = datetime(2026, 10, 20, 23, 50)
    w = client.post("/workouts").json()["id"]
    clock.now = datetime(2026, 10, 21, 0, 10)
    quest = client.get("/game/summary").json()["quest"]
    item = next(q for q in quest if q["metric"].startswith("sets:"))
    muscle = item["metric"].split(":")[1]
    pick = next(
        e
        for e in client.get("/exercises", params={"custom": False}).json()
        if any(m["muscle"] == muscle and m["weight"] >= 1 for m in e["muscles"])
        and e["measure"] == "reps"
        and e["section"] in ("gym", "calisthenics")
    )
    log(client, w, pick["id"], weight_kg=20, reps=8)
    quest = client.get("/game/summary").json()["quest"]
    assert next(q for q in quest if q["id"] == item["id"])["progress"] == 1


def test_unrealistic_holds_and_hold_edits(client, profile):
    plank = ex(client, "Plank")
    w = client.post("/workouts").json()["id"]
    r = client.post(f"/workouts/{w}/sets", json={"exercise_id": plank, "duration_s": 5000})
    assert r.status_code == 422 and "plausible" in r.json()["detail"]
    s = log(client, w, plank, duration_s=60)
    edited = client.patch(
        f"/workouts/{w}/sets/{s['set']['id']}", json={"reps": 40, "duration_s": 75}
    )
    assert (
        edited.status_code == 200
        and edited.json()["reps"] == 1
        and edited.json()["duration_s"] == 75
    )
    assert (
        client.patch(f"/workouts/{w}/sets/{s['set']['id']}", json={"duration_s": 9000}).status_code
        == 422
    )


def test_a_clock_jumping_back_keeps_sets_in_order(client, profile, clock):
    bench = ex(client, "Barbell Bench Press")
    w = client.post("/workouts").json()["id"]
    a = log(client, w, bench, weight_kg=60, reps=5)
    clock.now -= timedelta(hours=1)  # e.g. a time-zone change mid-session
    b = log(client, w, bench, weight_kg=60, reps=5)
    assert b["set"]["performed_at"] >= a["set"]["performed_at"]


def test_custom_exercises_cannot_game_muscle_quests_or_clash(client):
    base = {
        "name": "Everything Press", "section": "gym", "equipment": "barbell", "measure": "reps",
        "pattern": "push",
        "muscles": [{"muscle": m, "weight": 1} for m in ("quads", "lats", "abs", "glutes")],
    }  # fmt: skip
    r = client.post("/exercises", json=base)
    assert r.status_code == 422 and "at most 3 primary" in r.text
    cardio_reps = dict(
        base, name="Odd Run", section="cardio", muscles=[{"muscle": "quads", "weight": 1}]
    )
    assert client.post("/exercises", json=cardio_reps).status_code == 422
    clash = dict(
        base, name="My Press", muscles=[{"muscle": "triceps", "weight": 1}], aliases=["Pull-up"]
    )
    assert client.post("/exercises", json=clash).status_code == 409


def _csv(rows):
    header = (
        "Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit;Reps;RPE;Distance;"
        "Distance Unit;Seconds;Notes;Workout Notes;Workout Duration"
    )
    return "\n".join([header, *rows])


def test_import_skips_future_dates_and_sessions_already_logged(client, profile, clock):
    clock.now = datetime(2026, 10, 20, 19, 0)
    squat = ex(client, "Back Squat")
    w = client.post("/workouts").json()["id"]
    log(client, w, squat, weight_kg=80, reps=5)
    rows = [
        "2026-10-20 18:45:00;Legs;Squat (Barbell);1;80;kg;5;;;;0;;;45m",  # the same session
        "2026-12-01 18:00:00;Legs;Squat (Barbell);1;80;kg;5;;;;0;;;45m",  # future
        "2026-10-10 18:00:00;Legs;Squat (Barbell);1;80;kg;5;;;;0;;;45m",  # fine
    ]
    rep = client.post("/import/strong", json={"csv": _csv(rows), "dry_run": True}).json()
    assert rep["workouts"] == 1 and rep["skipped_duplicates"] == 1
    assert any("future" in w for w in rep["warnings"]) and any(
        "already logged" in w for w in rep["warnings"]
    )


def test_every_training_quest_can_be_completed(client, profile, clock):
    """Over two weeks of generated quests, logging the suggested work always completes it."""
    exercises = client.get("/exercises").json()
    for _ in range(14):
        quest = client.get("/game/summary").json()["quest"]
        for item in [q for q in quest if q["metric"].startswith("sets:") and not q["completed_at"]]:
            muscle = item["metric"].split(":")[1]
            suggested = item["detail"].split("Suggested: ")[1].split(".")[0]
            e = next(x for x in exercises if x["name"] == suggested)
            assert any(m["muscle"] == muscle and m["weight"] >= 1 for m in e["muscles"])
            w = client.post("/workouts").json()["id"]
            for _ in range(item["target"]):
                if e["measure"] == "time":
                    body = {"duration_s": 600}
                elif e["measure"] == "hold":
                    body = {"duration_s": 30}
                else:
                    body = {"weight_kg": 20, "reps": 8}
                log(client, w, e["id"], **body)
            done = next(
                q for q in client.get("/game/summary").json()["quest"] if q["id"] == item["id"]
            )
            assert done["completed_at"] is not None, item
        clock.now += timedelta(days=1)
