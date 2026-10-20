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
    seed_demo.seed(days=14, wipe=True)

    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        weights = c.get("/body-metrics", params={"days": 30}).json()
        assert 8 <= len(weights) <= 13
        assert all(67 <= w["weight_kg"] <= 70 for w in weights)
        assert {m["site"] for m in c.get("/measurements").json()} == {"waist", "arm", "chest"}
        assert len(c.get("/checkins").json()) == 13  # today is left for the user
        sections = {w["section"] for w in c.get("/workouts", params={"limit": 50}).json()}
        assert sections == {"gym", "cardio", "meditation"}
        assert c.get("/profile").json()["target_weight_kg"] == 72
        assert c.get("/settings").json()["sessions_per_week"] == 5
        assert c.get("/progress/eta").status_code == 200


def test_seed_demo_wipe_is_repeatable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASCEND_TOKEN", "t")
    seed_demo.seed(days=7, wipe=True)
    seed_demo.seed(days=7, wipe=True)
    app = create_app(load_settings(), outbox_interval=0)
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        assert len(c.get("/checkins").json()) == 6
        assert len(c.get("/measurements").json()) == 6  # 3 sites x first and last day
