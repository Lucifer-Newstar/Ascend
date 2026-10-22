"""Security/code review M5 (export loses data) and L15 (CSV formula injection)."""

from __future__ import annotations

import csv
import io
from datetime import timedelta

from app.modules.io import formats
from tests.api.test_custom_exercises import analyze, body_from


def _ex(client, q: str) -> int:
    return next(e["id"] for e in client.get("/exercises", params={"q": q}).json())


def _log(client, clock) -> None:
    squat, run = _ex(client, "Back Squat"), _ex(client, "Running")
    w = client.post("/workouts").json()["id"]
    for kg in (80, 85):
        client.post(f"/workouts/{w}/sets", json={"exercise_id": squat, "weight_kg": kg, "reps": 5})
    assert client.post(f"/workouts/{w}/finish").status_code == 200
    clock.now += timedelta(hours=3)
    w2 = client.post("/workouts").json()["id"]
    r = client.post(
        f"/workouts/{w2}/sets",
        json={"exercise_id": run, "duration_s": 1800, "distance_m": 5000, "avg_hr": 150},
    )
    assert r.status_code == 201, r.text
    client.post(f"/workouts/{w2}/finish")


def test_workout_csv_keeps_cardio_fields(client, clock, profile) -> None:
    _log(client, clock)
    rows = list(csv.DictReader(io.StringIO(client.get("/export/csv/workouts").text)))
    run = next(r for r in rows if r["Seconds"])
    assert (run["Seconds"], run["Distance"], run["Distance Unit"], run["Avg HR"]) == (
        "1800",
        "5.0",
        "km",
        "150",
    )


def test_workout_csv_reimports(client, clock, profile) -> None:
    """The export is read back by ASCEND's own Strong importer with nothing lost."""
    _log(client, clock)
    text = client.get("/export/csv/workouts").text
    assert formats.detect_format(text) == "strong_csv"
    parsed = formats.parse_strong(text)
    assert [(p.exercise, p.weight_kg, p.reps) for p in parsed[:2]] == [
        ("Back Squat", 80.0, 5),
        ("Back Squat", 85.0, 5),
    ]
    run = parsed[2]
    assert (run.duration_s, run.distance_m) == (1800, 5000.0)
    # Both sets of the first session are one workout (grouped by its start time).
    assert parsed[0].started_at == parsed[1].started_at != parsed[2].started_at
    r = client.post("/import/strong", json={"csv": text})
    assert r.status_code == 200, r.text


def test_csv_defuses_formula_names(client, profile) -> None:
    client.put("/settings", json={"ai_enabled": False})
    name = "=HYPERLINK(evil)"
    body = body_from(
        analyze(client, name),
        section="gym",
        measure="reps",
        muscles=[{"muscle": "external_obliques", "weight": 1.0}],
    )
    made = client.post("/exercises", json=body)
    assert made.status_code == 201, made.text
    w = client.post("/workouts").json()["id"]
    client.post(
        f"/workouts/{w}/sets", json={"exercise_id": made.json()["id"], "weight_kg": 10, "reps": 5}
    )
    rows = list(csv.DictReader(io.StringIO(client.get("/export/csv/workouts").text)))
    assert rows[0]["Exercise Name"] == "'=HYPERLINK(evil)"
    # ... and the importer reads the original name back.
    text = client.get("/export/csv/workouts").text
    assert formats.parse_strong(text)[0].exercise == name


def test_json_export_has_everything_the_user_entered(client, clock, profile) -> None:
    _log(client, clock)
    client.put("/profile", json={**profile_body(), "target_weight_kg": 75})
    client.put("/settings", json={"ai_enabled": False})
    assert client.post("/body-metrics", json={"weight_kg": 71.5, "waist_cm": 80}).status_code == 201
    assert client.post("/measurements", json={"site": "waist", "cm": 80}).status_code == 201
    assert (
        client.post(
            "/checkins", json={"sleep": 4, "energy": 3, "soreness": "some", "mood": 4}
        ).status_code
        == 201
    )
    made = client.post(
        "/exercises",
        json=body_from(
            analyze(client, "Zercher carry walk"),
            muscles=[{"muscle": "external_obliques", "weight": 1.0}],
        ),
    )
    assert made.status_code == 201, made.text

    data = client.get("/export/json").json()
    assert data["export_schema_version"] == 2
    assert data["profile"]["target_weight_kg"] == 75
    assert isinstance(data["profile"]["equipment"], list)
    assert [b["weight_kg"] for b in data["body_metrics"]] == [71.5]
    assert data["measurements"][0]["site"] == "waist"
    assert data["checkins"][0]["sleep"] == 4
    assert data["settings"]  # the ai_enabled switch, at least
    assert [e["name"] for e in data["custom_exercises"]] == ["Zercher carry walk"]
    assert "skill_unlocks" in data
    run = next(s for w in data["workouts"] for s in w["sets"] if s["duration_s"])
    assert (run["distance_m"], run["avg_hr"]) == (5000.0, 150)


def profile_body() -> dict:
    return {
        "name": "Navin",
        "age": 21,
        "sex": "male",
        "height_cm": 175,
        "weight_kg": 70,
        "goal": "bulk",
        "activity": "moderate",
    }
