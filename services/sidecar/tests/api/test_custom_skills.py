from datetime import timedelta

from app.modules.skills.catalog import SKILLS


def ex_id(client, name):
    return next(
        e["id"] for e in client.get("/exercises", params={"q": name}).json() if e["name"] == name
    )


def body(client, **over):
    b = {
        "name": "Push-up ladder",
        "family": "push",
        "summary": "My own push-up goals.",
        "steps": [
            {
                "name": "Ten in a row",
                "exercise_id": ex_id(client, "Push-up"),
                "sets": 3,
                "reps": 10,
            },
            {"exercise_id": ex_id(client, "Diamond Push-up"), "sets": 3, "reps": 8},
        ],
    }
    b.update(over)
    return b


def test_catalog_has_17_trees():
    assert len(SKILLS) == 17
    assert {"hanging_leg_raise", "weighted_pull_up", "one_arm_hang", "split_squat",
            "plyo_push_up"} <= {s.key for s in SKILLS}  # fmt: skip


def test_create_list_and_show_in_the_skill_list(client):
    r = client.post("/skills/custom", json=body(client))
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["key"] == f"custom_{row['id']}" and len(row["steps"]) == 2
    assert row["steps"][1]["name"] == "Diamond Push-up"
    listed = client.get("/skills").json()
    mine = next(s for s in listed if s["key"] == row["key"])
    assert mine["custom"] and mine["steps_total"] == 2 and mine["steps_unlocked"] == 0
    assert not any(s["custom"] for s in listed if s["key"] != row["key"])
    d = client.get(f"/skills/{row['key']}").json()
    assert d["steps"][0]["criteria"][0]["text"] == "3\u00d710 Push-up"
    assert all(s["xp"] == 0 for s in d["steps"])
    assert client.get("/skills/custom").json()[0]["name"] == "Push-up ladder"


def test_logged_sets_unlock_a_custom_milestone_without_xp(client, profile, clock):
    row = client.post("/skills/custom", json=body(client)).json()
    pid = ex_id(client, "Push-up")
    for _day in range(2):  # a goal counts once it is shown in two sessions
        w = client.post("/workouts").json()["id"]
        for _ in range(3):
            client.post(f"/workouts/{w}/sets", json={"exercise_id": pid, "reps": 12})
        client.post(f"/workouts/{w}/finish")
        clock.now += timedelta(days=1)
    d = client.get(f"/skills/{row['key']}").json()
    assert d["steps"][0]["status"] == "unlocked"
    unlocks = client.get("/skills/unlocks").json()
    mine = [u for u in unlocks if u["skill_key"] == row["key"]]
    assert mine and mine[0]["xp"] == 0


def test_validation(client):
    hold_id = ex_id(client, "Plank")
    bad = body(client, steps=[{"exercise_id": hold_id, "reps": 10}])
    r = client.post("/skills/custom", json=bad)
    assert r.status_code == 422 and "hold" in r.json()["detail"]
    r = client.post("/skills/custom", json=body(client, steps=[{"exercise_id": 999999, "reps": 5}]))
    assert r.status_code == 422
    r = client.post("/skills/custom", json=body(client, name="Muscle-up"))
    assert r.status_code == 422 and "already exists" in r.json()["detail"]
    r = client.post("/skills/custom", json=body(client, family="dance"))
    assert r.status_code == 422


def test_update_and_delete(client):
    row = client.post("/skills/custom", json=body(client)).json()
    b = body(client, name="Ladder v2")
    b["steps"] = b["steps"][:1]
    r = client.put(f"/skills/custom/{row['id']}", json=b)
    assert r.status_code == 200 and r.json()["name"] == "Ladder v2" and len(r.json()["steps"]) == 1
    assert client.delete(f"/skills/custom/{row['id']}").status_code == 204
    assert client.get(f"/skills/{row['key']}").status_code == 404
    assert all(s["key"] != row["key"] for s in client.get("/skills").json())
    assert client.delete(f"/skills/custom/{row['id']}").status_code == 404
