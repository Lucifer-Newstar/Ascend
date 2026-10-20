"""Request bodies reject unknown fields (StrictIn); PUT /profile deliberately ignores them."""

from tests.api.test_workouts import exercise_id


def test_typo_in_set_body_is_a_422_naming_the_field(client, profile):
    bench = exercise_id(client, "Barbell Bench Press")
    w = client.post("/workouts").json()
    r = client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": bench, "weigth_kg": 60, "reps": 8}
    )
    assert r.status_code == 422
    locs = [e["loc"][-1] for e in r.json()["detail"]]
    assert "weigth_kg" in locs
    # nothing was logged
    assert client.get(f"/workouts/{w['id']}").json()["sets"] == []


def test_unknown_fields_rejected_on_settings_and_body_metrics(client, profile):
    assert client.put("/settings", json={"theme": "light", "colour": "red"}).status_code == 422
    assert client.get("/settings").json()["theme"] == "dark"  # unchanged
    assert client.post("/body-metrics", json={"weight_kg": 70, "bodyfat": 12}).status_code == 422
    assert client.post("/body-metrics", json={"weight_kg": 70}).status_code in (200, 201)


def test_literal_values_are_not_loosened(client, profile):
    # Trimming applies to free-text fields only; enum-like values must match exactly.
    assert client.put("/settings", json={"theme": " light "}).status_code == 422


def test_profile_put_ignores_read_only_fields_echoed_back(client, profile):
    current = client.get("/profile").json()
    current["age"] = 22
    r = client.put("/profile", json=current)
    assert r.status_code == 200, r.text
    assert r.json()["age"] == 22
