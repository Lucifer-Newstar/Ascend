"""The demo seeder fills every screen's data through the real services."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.devtools import seed_demo
from app.main import create_app


def test_seed_demo_fills_progress_activity_and_checkins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCEND_TOKEN", "t")
    seed_demo.seed(days=14, wipe=True, history_weeks=0)

    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        weights = c.get("/body-metrics", params={"days": 30}).json()
        assert 8 <= len(weights) <= 13
        assert all(67 <= w["weight_kg"] <= 70 for w in weights)
        assert {m["site"] for m in c.get("/measurements").json()} == {"waist", "arm", "chest"}
        assert len(c.get("/checkins").json()) == 13  # today is left for the user
        sections = {w["section"] for w in c.get("/workouts", params={"limit": 50}).json()}
        assert sections == {"gym", "calisthenics", "cardio", "meditation"}
        skills = {s["key"]: s for s in c.get("/skills").json()}
        assert skills["muscle_up"]["current_step"] == "pull_up"
        assert skills["muscle_up"]["pct_to_next"] == 95.0  # 3x8 pull-ups once; once more unlocks
        assert c.get("/skills/front_lever").json()["eta"]["days"] is not None
        assert c.get("/profile").json()["target_weight_kg"] == 72
        assert c.get("/settings").json()["sessions_per_week"] == 5
        assert c.get("/progress/eta").status_code == 200


def test_seed_demo_wipe_is_repeatable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCEND_TOKEN", "t")
    seed_demo.seed(days=7, wipe=True, history_weeks=0)
    seed_demo.seed(days=7, wipe=True, history_weeks=0)
    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        assert len(c.get("/checkins").json()) == 6
        assert len(c.get("/measurements").json()) == 6  # 3 sites x first and last day


def test_seed_demo_wipe_removes_user_added_exercises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCEND_TOKEN", "t")
    seed_demo.seed(days=3, wipe=True, history_weeks=0)
    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        library = len(c.get("/exercises").json())
        c.put("/settings", json={"ai_enabled": False})
        body = {
            "name": "Banded Pallof Hold", "section": "gym", "equipment": "band",
            "measure": "hold", "pattern": "isometric",
            "muscles": [{"muscle": "obliques", "weight": 1}],
        }  # fmt: skip
        assert c.post("/exercises", json=body).status_code == 201
    seed_demo.seed(days=3, wipe=True, history_weeks=0)
    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        assert c.get("/exercises", params={"custom": True}).json() == []
        assert len(c.get("/exercises").json()) == library


def test_seed_demo_history_gives_the_engines_trends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCEND_TOKEN", "t")
    seed_demo.seed(days=3, wipe=True, history_weeks=4)
    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        gym = c.get("/workouts", params={"limit": 100, "section": "gym"}).json()
        assert len(gym) >= 15  # about 3 of every 4 days over 4 weeks, plus the fortnight's
        bench = next(
            e["id"]
            for e in c.get("/exercises", params={"q": "Barbell Bench Press"}).json()
            if e["name"] == "Barbell Bench Press"
        )
        t = c.get(f"/intelligence/progression/{bench}").json()
        assert t["change"] != "first" and len(t["e1rm"]["series"]) >= 5
        series = t["e1rm"]["series"]
        assert series == sorted(series, key=lambda p: p["at"])
        assert series[-1]["value"] > series[0]["value"]  # the earlier weeks progress
        groups = c.get("/intelligence/recovery").json()["groups"]
        assert all(g["updated_at"] is not None for g in groups)  # refitted after sessions
