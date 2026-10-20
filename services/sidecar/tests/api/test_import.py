from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "import"


def csv(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_dry_run_reports_without_writing(client, profile):
    r = client.post("/import/strong", json={"csv": csv("strong_classic.csv")})
    assert r.status_code == 200
    report = r.json()
    assert report["dry_run"] is True
    assert report["format"] == "strong_csv"
    assert report["workouts"] == 2
    # 7 rows minus 1 warm-up minus the unknown Zercher good morning
    assert report["sets"] == 6
    assert report["skipped_warmups"] == 1
    assert report["unmatched_exercises"] == ["Zercher Good Morning (Barbell)"]
    assert report["matched_exercises"]["Squat (Barbell)"] == "Back Squat"
    assert client.get("/workouts").json() == []


def test_import_writes_finished_workouts_with_converted_units(client, profile):
    r = client.post("/import/strong", json={"csv": csv("strong_classic.csv"), "dry_run": False})
    assert r.status_code == 200
    assert r.json()["dry_run"] is False
    workouts = client.get("/workouts").json()
    assert len(workouts) == 2
    legs = workouts[0]  # newest first
    assert legs["day"] == "2026-09-03"
    assert legs["finished_at"] == "2026-09-03T08:20:00"
    detail = client.get(f"/workouts/{legs['id']}").json()
    squat = next(s for s in detail["sets"] if s["exercise_name"] == "Back Squat")
    assert squat["weight_kg"] == pytest.approx(102.06, abs=0.01)
    run = next(s for s in detail["sets"] if s["exercise_name"] == "Running")
    assert run["duration_s"] == 1500 and run["distance_m"] == pytest.approx(5150, abs=1)


def test_importing_the_same_file_twice_adds_nothing(client, profile):
    body = {"csv": csv("hevy.csv"), "dry_run": False}
    first = client.post("/import/hevy", json=body).json()
    second = client.post("/import/hevy", json=body).json()
    assert first["workouts"] == 2
    assert second["workouts"] == 0 and second["skipped_duplicates"] == 2
    assert len(client.get("/workouts").json()) == 2


def test_imported_bests_become_prs_but_earn_no_xp(client, profile):
    xp_before = client.get("/game/summary").json()["xp"]["total"]
    client.post("/import/hevy", json={"csv": csv("hevy.csv"), "dry_run": False})
    prs = {p["exercise"]: p for p in client.get("/prs").json()}
    assert prs["Barbell Bench Press"]["weight_kg"] == 70
    assert client.get("/game/summary").json()["xp"]["total"] == xp_before


def test_warmups_can_be_included(client, profile):
    r = client.post("/import/hevy", json={"csv": csv("hevy.csv"), "include_warmups": True})
    assert r.json()["skipped_warmups"] == 0
    assert r.json()["sets"] == 4


def test_strong_2025_in_pounds(client, profile):
    r = client.post(
        "/import/strong",
        json={"csv": csv("strong_2025.csv"), "unit": "lb", "dry_run": False},
    )
    assert r.json()["format"] == "strong_csv_2025"
    w = client.get("/workouts").json()[0]
    sets = client.get(f"/workouts/{w['id']}").json()["sets"]
    pulldown = next(s for s in sets if s["exercise_name"] == "Lat Pulldown")
    assert pulldown["weight_kg"] == pytest.approx(61.23, abs=0.01)


def test_out_of_range_rows_are_dropped_with_a_warning(client, profile):
    text = (
        "Date,Workout Name,Duration,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,"
        "Notes,Workout Notes,RPE\n"
        "2026-09-10 18:00:00,Heavy,1h,Deadlift (Barbell),1,900,1,0,0,,,\n"
        "2026-09-10 18:00:00,Heavy,1h,Deadlift (Barbell),2,180,3,0,0,,,\n"
    )
    report = client.post("/import/strong", json={"csv": text}).json()
    assert report["sets"] == 1
    assert report["warnings"] == ["2026-09-10 Deadlift (Barbell) set 1: weight outside 0-500 kg"]


def test_imported_sets_count_towards_muscle_load(client, profile, clock):
    text = (
        "Date,Workout Name,Duration,Exercise Name,Set Order,Weight,Reps,Distance,Seconds,"
        "Notes,Workout Notes,RPE\n"
        f"{clock.now:%Y-%m-%d} 07:00:00,Legs,1h,Squat (Barbell),1,80,5,0,0,,,9\n"
    )
    client.post("/import/strong", json={"csv": text, "dry_run": False})
    quads = next(m for m in client.get("/muscles").json() if m["key"] == "quads")
    assert quads["es_7d"] > 0


@pytest.mark.parametrize(
    ("path", "text", "message"),
    [
        ("/import/strong", "name,kcal\nrice,200\n", "Strong or Hevy"),
        ("/import/hevy", None, "not a Hevy export"),
        (
            "/import/strong",
            "Date,Workout Name,Duration,Exercise Name,Set Order,Weight\n",
            "no sets",
        ),
    ],
)
def test_bad_files_get_a_readable_422(client, profile, path, text, message):
    body = text if text is not None else csv("strong_2025.csv")
    r = client.post(path, json={"csv": body})
    assert r.status_code == 422
    assert message in r.json()["detail"]


def test_imported_workouts_say_where_they_came_from(client, profile):
    client.post("/import/hevy", json={"csv": csv("hevy.csv"), "dry_run": False})
    newest = client.get("/workouts").json()[0]
    assert newest["source"] == "hevy" and newest["title"] == "Cardio"
    detail = client.get(f"/workouts/{newest['id']}").json()
    assert detail["source"] == "hevy"
    logged = client.post("/workouts").json()
    assert logged["source"] == "app" and logged["title"] == ""
