"""Timed holds (plank, L-sit, levers...) end to end: log, PR, edit, muscle load, import."""

STRONG_HEADER = (
    "Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit;Reps;RPE;Distance;"
    "Distance Unit;Seconds;Notes;Workout Notes;Workout Duration"
)


def ex(client, name):
    return next(e for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name)


def log(client, w, exercise_id, **body):
    return client.post(f"/workouts/{w}/sets", json={"exercise_id": exercise_id, **body})


def test_a_hold_needs_seconds_and_is_one_effort_per_set(client, profile):
    plank = ex(client, "Plank")
    assert plank["measure"] == "hold" and plank["time_based"] is False
    w = client.post("/workouts").json()["id"]
    r = log(client, w, plank["id"], reps=8)
    assert r.status_code == 422 and "hold" in r.json()["detail"]
    r = log(client, w, plank["id"], duration_s=45, reps=8, rpe=8)
    assert r.status_code == 201, r.text
    s = r.json()["set"]
    assert (s["duration_s"], s["reps"], s["e1rm"], s["measure"]) == (45, 1, None, "hold")


def test_longest_hold_is_the_pr_and_added_weight_is_not_an_e1rm(client, profile):
    lever = ex(client, "Tuck Front Lever")
    w = client.post("/workouts").json()["id"]
    first = log(client, w, lever["id"], duration_s=10).json()["set"]
    longer = log(client, w, lever["id"], duration_s=14, weight_kg=0).json()["set"]
    shorter = log(client, w, lever["id"], duration_s=12, weight_kg=5).json()["set"]
    assert first["is_pr"] is False  # nothing to beat yet, same rule as lifts
    assert longer["is_pr"] is True and shorter["is_pr"] is False
    assert shorter["e1rm"] is None and shorter["weight_kg"] == 5


def test_editing_a_hold_recomputes_the_pr(client, profile):
    lsit = ex(client, "L-sit")
    w = client.post("/workouts").json()["id"]
    a = log(client, w, lsit["id"], duration_s=10).json()["set"]
    b = log(client, w, lsit["id"], duration_s=15).json()["set"]
    assert b["is_pr"] is True
    # The first one was a typo for 20 s: now it is the best and the second is not a PR.
    client.patch(f"/workouts/{w}/sets/{a['id']}", json={"duration_s": 20})
    sets = {s["id"]: s for s in client.get(f"/workouts/{w}").json()["sets"]}
    assert sets[b["id"]]["is_pr"] is False and sets[b["id"]]["e1rm"] is None


def test_a_hold_counts_as_a_set_for_muscle_load(client, profile):
    lever = ex(client, "Tuck Front Lever")
    w = client.post("/workouts").json()["id"]
    log(client, w, lever["id"], duration_s=12, rpe=9)
    lats = next(m for m in client.get("/muscles").json() if m["key"] == "lats")
    assert lats["es_7d"] == 1.0  # weight 1.0 x effort 1.0, one set


def test_imported_plank_keeps_its_seconds(client, profile):
    csv = "\n".join(
        [
            STRONG_HEADER,
            "2026-09-01 18:02:11;Core;Plank;1;0;kg;0;;;;75;;;20m",
            "2026-09-01 18:02:11;Core;Plank;2;10;kg;0;;;;60;;;20m",
        ]
    )
    r = client.post("/import/strong", json={"csv": csv, "dry_run": False})
    assert r.status_code == 200 and r.json()["sets"] == 2, r.text
    wid = client.get("/workouts").json()[0]["id"]
    sets = client.get(f"/workouts/{wid}").json()["sets"]
    assert [(s["duration_s"], s["reps"], s["weight_kg"], s["e1rm"]) for s in sets] == [
        (75, 1, 0, None),
        (60, 1, 10, None),
    ]
