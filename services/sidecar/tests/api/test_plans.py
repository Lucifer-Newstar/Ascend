"""/plans (programs-v1, ADR-0020): choosing a program, the next session with prog-v1
targets, the rotation read from finished workouts, and leaving."""

from datetime import timedelta


def ex_ids(client) -> dict[str, int]:
    return {e["name"]: e["id"] for e in client.get("/exercises", params={"limit": 500}).json()}


def train(client, clock, names: list[str], ids: dict[str, int], day_offset: int = 0) -> None:
    now = clock.now
    clock.now = now + timedelta(days=day_offset)
    w = client.post("/workouts", json={"section": "gym"}).json()
    for n in names:
        r = client.post(
            f"/workouts/{w['id']}/sets",
            json={"exercise_id": ids[n], "weight_kg": 40, "reps": 8, "rpe": 8},
        )
        assert r.status_code == 201, r.text
    assert client.post(f"/workouts/{w['id']}/finish").status_code == 200
    clock.now = now


def test_catalog_lists_programs_with_library_ids(client):
    progs = {p["key"]: p for p in client.get("/plans/programs").json()}
    assert {"full_body_3", "upper_lower_4", "ppl_6", "home_full_body_3"} <= set(progs)
    ul = progs["upper_lower_4"]
    assert ul["days_per_week"] == 4 and ul["fits_equipment"] is True
    assert all(i["exercise_id"] is not None for d in ul["days"] for i in d["items"])


def test_no_program_is_null_until_one_is_chosen(client):
    r = client.get("/plans/current")
    assert r.status_code == 200 and r.json() is None
    assert client.delete("/plans/current").status_code == 404
    assert client.put("/plans/current", json={"program_key": "nope"}).status_code == 422


def test_choose_follow_and_leave(client, clock):
    r = client.put("/plans/current", json={"program_key": "upper_lower_4"})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["next"]["key"] == "upper_a" and plan["sessions_done"] == 0
    assert plan["started_on"] == clock.now.date().isoformat()
    first = plan["next"]["items"][0]
    # No history yet: no prog-v1 target, the card shows the program's own 4 x 5-8.
    assert first["exercise"] == "Barbell Bench Press" and first["target"] is None
    assert (first["sets"], first["rep_low"], first["rep_high"]) == (4, 5, 8)
    assert plan["why"]["inputs"]["next_day"] == "upper_a"

    ids = ex_ids(client)
    upper_a = [i["exercise"] for i in plan["next"]["items"]]
    train(client, clock, upper_a[:4], ids)  # 4 of 6: counts as Upper A
    plan = client.get("/plans/current").json()
    assert plan["next"]["key"] == "lower_a" and plan["sessions_done"] == 1
    # Lower A tomorrow (3 of 5 exercises); three days later Upper B is next, and Upper A's
    # bench, trained once, now has a prog-v1 target with the program's 4 sets.
    train(client, clock, ["Back Squat", "Romanian Deadlift", "Leg Press"], ids, day_offset=1)
    clock.now = clock.now + timedelta(days=3)
    later = client.get("/plans/current").json()
    assert later["next"]["key"] == "upper_b" and later["sessions_done"] == 2
    clock.now = clock.now - timedelta(days=3)
    assert plan["recent"][0]["key"] == "upper_a"

    # Choosing the same program again keeps its progress; another one starts over.
    same = client.put("/plans/current", json={"program_key": "upper_lower_4"}).json()
    assert same["id"] == plan["id"] and same["sessions_done"] == 1
    other = client.put("/plans/current", json={"program_key": "full_body_3"}).json()
    assert other["id"] != plan["id"] and other["next"]["key"] == "a1"

    assert client.delete("/plans/current").status_code == 204
    assert client.get("/plans/current").json() is None


def test_sets_in_the_open_workout_show_on_the_next_session(client):
    client.put("/plans/current", json={"program_key": "full_body_3"})
    ids = ex_ids(client)
    w = client.post("/workouts", json={"section": "gym"}).json()
    for _ in range(2):
        client.post(
            f"/workouts/{w['id']}/sets",
            json={"exercise_id": ids["Back Squat"], "weight_kg": 60, "reps": 5, "rpe": 8},
        )
    items = {i["exercise"]: i for i in client.get("/plans/current").json()["next"]["items"]}
    assert items["Back Squat"]["done_sets"] == 2 and items["Barbell Row"]["done_sets"] == 0


def test_targets_use_the_programs_rep_range(client, clock):
    """ppl_6 gives Lateral Raise 12-20. 3 x 14 sits inside that range, so the next target
    adds a rep; the library's 8-12 isolation default made it a load jump (QA pass 4: the
    Train card read "3 x 1 @ 18 kg" and Today read "3 x 12-20" for the same move)."""
    client.put("/plans/current", json={"program_key": "ppl_6"})
    ids = ex_ids(client)
    raise_id = ids["Lateral Raise"]
    w = client.post("/workouts", json={"section": "gym"}).json()
    for _ in range(3):
        r = client.post(
            f"/workouts/{w['id']}/sets",
            json={"exercise_id": raise_id, "weight_kg": 10, "reps": 14, "rpe": 8},
        )
        assert r.status_code == 201, r.text
    assert client.post(f"/workouts/{w['id']}/finish").status_code == 200
    clock.now += timedelta(days=3)

    t = client.get(f"/intelligence/progression/{raise_id}").json()
    assert t["rep_range"] == [12, 20]
    assert (t["change"], t["reps"], t["weight_kg"]) == ("up_reps", 15, 10)
    assert t["explanation"]["inputs"]["range_from"] == "your program's range"
    plan = client.get("/plans/current").json()
    item = next(i for i in plan["next"]["items"] if i["exercise"] == "Lateral Raise")
    assert item["target"] == "3 × 15 @ 10 kg, RPE 8"

    client.delete("/plans/current")  # not following a program: the library range again
    t = client.get(f"/intelligence/progression/{raise_id}").json()
    assert t["rep_range"] == [8, 12] and t["change"] == "up_load"
