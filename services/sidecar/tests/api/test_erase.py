"""Start fresh: POST /data/erase deletes the user's data and keeps the libraries."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _counts(client: TestClient) -> tuple[int, int]:
    exercises = len(client.get("/exercises").json())
    foods = len(client.get("/foods", params={"q": ""}).json())
    return exercises, foods


def test_erase_needs_the_confirm_word(client: TestClient) -> None:
    assert client.post("/data/erase", json={}).status_code == 422
    assert client.post("/data/erase", json={"confirm": "yes"}).status_code == 422


def test_erase_keeps_libraries_and_preferences(client: TestClient, profile: dict, settings) -> None:
    before = _counts(client)
    client.put("/settings", json={"theme": "light", "sessions_per_week": 5})
    w = client.post("/workouts", json={}).json()
    ex = client.get("/exercises").json()[0]
    client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": ex["id"], "reps": 5, "weight_kg": 40}
    )
    photos = settings.data_dir / "photos"
    photos.mkdir()
    (photos / "a.jpg").write_bytes(b"x")

    r = client.post("/data/erase", json={"confirm": "erase"})
    assert r.status_code == 200, r.text
    erased = r.json()["erased"]
    assert erased["profile"] == 1 and erased["workout_sets"] >= 1
    assert erased["photo_files"] == 1 and not photos.exists()
    assert r.json()["safety_backup"].endswith(".ascendbak")

    assert client.get("/dashboard").json()["has_profile"] is False
    assert client.get("/workouts").json() == []
    assert _counts(client) == before  # exercise library and food table untouched
    s = client.get("/settings").json()
    assert s["theme"] == "light"  # a preference: kept
    assert s["sessions_per_week"] == 3  # about the user: back to the default
