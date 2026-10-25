"""v1.4 habit engine (schedule-v1): training days, planned vs done, short sessions."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

# The test clock starts on Tuesday 2026-10-20.


def _train(client: TestClient, name: str = "Push-up") -> None:
    ex = next(e["id"] for e in client.get("/exercises", params={"q": name}).json()
              if e["name"] == name)  # fmt: skip
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": ex, "reps": 10, "weight_kg": 0})
    client.post(f"/workouts/{w}/finish")


def test_no_schedule_then_your_own_days(client: TestClient, profile) -> None:
    s = client.get("/schedule").json()
    assert s["source"] == "none" and s["days"] == []
    r = client.put("/schedule", json={"days": [4, 0, 2, 2], "time": "18:30"})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s == {**s, "days": [0, 2, 4], "time": "18:30", "source": "you", "label": "Mon, Wed, Fri"}
    assert client.get("/settings").json()["sessions_per_week"] == 3


def test_bad_days_or_time_are_refused(client: TestClient, profile) -> None:
    assert client.put("/schedule", json={"days": [7]}).status_code == 422
    assert client.put("/schedule", json={"days": []}).status_code == 422
    assert client.put("/schedule", json={"days": [1], "time": "7pm"}).status_code == 422
    assert client.put("/schedule", json={"days": [1], "time": ""}).json()["time"] is None


def test_the_program_suggests_days_until_you_pick(client: TestClient, profile) -> None:
    client.put("/plans/current", json={"program_key": "bodyweight_starter_3"})
    s = client.get("/schedule").json()
    assert s["source"] == "program" and len(s["days"]) == 3


def test_week_view_shows_planned_vs_done_and_the_next_sessions(
    client: TestClient, profile, clock
) -> None:
    client.put("/plans/current", json={"program_key": "bodyweight_starter_3"})
    client.put("/schedule", json={"days": [0, 1, 3, 5]})
    _train(client)  # Tue
    w = client.get("/schedule/week").json()
    assert w["week_start"] == "2026-10-19" and w["source"] == "you" and not w["custom"]
    assert [d["planned"] for d in w["days"]] == [True, True, False, True, False, True, False]
    tue, thu, sat = w["days"][1], w["days"][3], w["days"][5]
    assert tue["done"] and tue["today"] and tue["session"] is None
    assert thu["session"] and sat["session"] and thu["session"] != sat["session"]
    assert w["planned"] == 4 and w["done"] == 1


def test_short_session_is_ten_minutes_and_counts_for_the_streak(
    client: TestClient, profile, clock
) -> None:
    assert client.get("/schedule/short-session").json() is None
    client.put("/plans/current", json={"program_key": "bodyweight_starter_3"})
    r = client.get("/schedule/short-session").json()
    assert r["minutes"] <= 10 and 1 <= len(r["items"]) <= 3
    assert all(i["sets"] == 2 and i["rest_s"] <= 45 for i in r["items"])
    assert "counts for your streak" in r["note"]
    first = r["items"][0]
    w = client.post("/workouts").json()["id"]
    client.post(
        f"/workouts/{w}/sets",
        json={"exercise_id": first["exercise_id"], "reps": first["rep_low"], "weight_kg": 0},
    )
    s = client.get("/game/summary").json()["streak"]
    assert s["active_today"] is True and s["current"] == 1
