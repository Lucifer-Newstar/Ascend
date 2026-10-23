from datetime import timedelta

from app.modules.skills.catalog import all_exercise_names


def ex_id(client, name):
    return next(
        e["id"] for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name
    )


def hold_sets(client, exercise_id, seconds, n=3):
    w = client.post("/workouts").json()["id"]
    out = [
        client.post(
            f"/workouts/{w}/sets", json={"exercise_id": exercise_id, "duration_s": seconds}
        ).json()
        for _ in range(n)
    ]
    client.post(f"/workouts/{w}/finish")
    return w, out


def test_every_catalog_exercise_is_in_the_library(client):
    names = {e["name"] for e in client.get("/exercises").json()}
    assert all_exercise_names() - names == set()


def test_list_and_detail(client):
    skills = client.get("/skills").json()
    assert len(skills) == 17
    mu = next(s for s in skills if s["key"] == "muscle_up")
    # v1.2: the entry step is where the tree starts, not an earned step.
    assert mu["current_step"] is None and mu["next_step"] == "scap_pull"
    assert mu["pct_to_next"] == 0 and not mu["acquired"]
    assert mu["steps_unlocked"] == 0 and mu["fits_equipment"] is True
    d = client.get("/skills/front_lever").json()
    assert d["current_step"] is None and d["next_step"] == "tuck"
    assert d["steps"][0]["criteria"][0]["text"] == "3\u00d75 Pull-up"
    assert (
        d["eta"]["days"] is None
        and d["eta"]["is_estimate"]
        and "not enough data" in d["eta"]["reason"]
    )
    assert d["sources"] and all(s["url"].startswith("https://") for s in d["sources"])
    assert any(s["uncertain"] for s in d["steps"])
    assert client.get("/skills/flying").status_code == 404


def test_unlock_pays_xp_once_and_appears_in_the_logged_set(client, profile, clock):
    hang = ex_id(client, "Dead Hang")
    hold_sets(client, hang, 30)
    assert client.get("/skills/muscle_up").json()["pct_to_next"] == 95.0
    clock.now += timedelta(days=1)
    w = client.post("/workouts").json()["id"]
    bodies = [
        client.post(f"/workouts/{w}/sets", json={"exercise_id": hang, "duration_s": 32}).json()
        for _ in range(3)
    ]
    assert [len(b["unlocks"]) for b in bodies] == [0, 0, 1]
    u = bodies[2]["unlocks"][0]
    assert (u["skill_key"], u["step_key"], u["final"]) == ("muscle_up", "scap_pull", False)
    assert u["xp"] == 30 and u["next_step_name"] == "Negative pull-up"
    mu = client.get("/skills/muscle_up").json()
    assert mu["current_step"] == "scap_pull" and mu["next_step"] == "negatives"
    # More hangs never pay the unlock again.
    more = client.post(f"/workouts/{w}/sets", json={"exercise_id": hang, "duration_s": 40}).json()
    assert more["unlocks"] == []
    assert len(client.get("/skills/unlocks").json()) == 1


def test_deleting_the_proof_revokes_the_step_and_its_xp(client, profile, clock):
    hang = ex_id(client, "Dead Hang")
    hold_sets(client, hang, 30)
    clock.now += timedelta(days=1)
    w = client.post("/workouts").json()["id"]
    sets = [
        client.post(f"/workouts/{w}/sets", json={"exercise_id": hang, "duration_s": 30}).json()
        for _ in range(3)
    ]
    assert sets[2]["unlocks"]
    before = client.get("/game/summary").json()["xp"]["total"]
    client.delete(f"/workouts/{w}/sets/{sets[2]['set']['id']}")
    assert client.get("/skills/unlocks").json() == []
    after = client.get("/game/summary").json()["xp"]["total"]
    assert before - after >= 30  # the skill XP (plus the set's own XP, handled separately)
    assert client.get("/skills/muscle_up").json()["current_step"] is None


def test_entry_steps_say_start_and_the_batch_call_returns_every_tree(client):
    trees = client.get("/skills/details").json()
    assert len(trees) == len(client.get("/skills").json())
    mu = next(s for s in trees if s["key"] == "muscle_up")
    assert mu["steps"][0]["status"] == "start" and mu["steps"][0]["unlocked_at"] is None


def test_trees_are_tagged_by_the_kit(client):
    client.put(
        "/profile",
        json={"age": 20, "sex": "male", "height_cm": 170, "weight_kg": 45, "goal": "bulk",
              "equipment": ["none"]},
    )  # fmt: skip
    fits = {s["key"]: s["fits_equipment"] for s in client.get("/skills").json()}
    assert fits["front_lever"] is False  # needs a bar
    assert fits["pistol"] is True  # floor only


def test_train_adds_capped_idempotent_quest_items_that_complete(client, profile):
    r = client.post("/skills/l_sit/train").json()
    assert r["added"] == 2 and "Plank to V-sit" in r["message"]
    again = client.post("/skills/l_sit/train").json()
    assert again["added"] == 0 and again["already_planned"] == 2
    client.post("/skills/front_lever/train")
    capped = client.post("/skills/dragon_flag/train").json()
    assert len(capped["items"]) == 4
    quest = client.get("/game/summary").json()["quest"]
    plank_item = next(q for q in quest if q["kind"] == "skill" and "Plank" in q["title"])
    plank = ex_id(client, "Plank")
    threshold = int(plank_item["title"].split("\u00d7")[1].split("s")[0])
    w = client.post("/workouts").json()["id"]
    for _ in range(plank_item["target"]):
        client.post(f"/workouts/{w}/sets", json={"exercise_id": plank, "duration_s": threshold})
    quest = client.get("/game/summary").json()["quest"]
    done = next(q for q in quest if q["id"] == plank_item["id"])
    assert done["completed_at"] is not None


def test_exercise_detail_lists_its_skill_trees(client):
    d = client.get(f"/exercises/{ex_id(client, 'Pull-up')}").json()
    roles = {(s["skill_key"], s["role"]) for s in d["skills"]}
    assert ("muscle_up", "step") in roles and ("front_lever", "feeder") in roles


def test_imported_history_unlocks_without_xp(client, profile):
    header = (
        "Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit;Reps;RPE;Distance;"
        "Distance Unit;Seconds;Notes;Workout Notes;Workout Duration"
    )
    rows = [header]
    for day in ("2026-10-10 18:00:00", "2026-10-12 18:00:00"):
        rows += [f"{day};Pull;Pull Up;{i};0;kg;9;;;;0;;;30m" for i in (1, 2, 3)]
    r = client.post("/import/strong", json={"csv": "\n".join(rows), "dry_run": False})
    assert r.json()["sets"] == 6
    fl = client.get("/skills/front_lever").json()
    assert fl["current_step"] == "tuck"  # 3x5 pull-ups proven by the import
    unlock = next(
        u
        for u in client.get("/skills/unlocks", params={"limit": 50}).json()
        if u["skill_key"] == "front_lever"
    )
    assert unlock["xp"] == 0 and unlock["source"] == "import"
