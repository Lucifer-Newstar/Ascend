from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

TOKEN = "test-token"


class FakeClock:
    """Mutable clock so tests can move time forward (recovery decay, streaks)."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 10, 20, 9, 0, 0))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Point Ollama at a closed port so the coach always takes the rules path in tests.
    return Settings(data_dir=tmp_path, db_url=f"sqlite:///{tmp_path / 'test.db'}", token=TOKEN,
                    ollama_host="http://127.0.0.1:9")


@pytest.fixture
def client(settings: Settings, clock: FakeClock) -> TestClient:
    app = create_app(settings, clock=clock)  # runs the real Alembic migrations
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as c:
        yield c


@pytest.fixture
def profile(client: TestClient) -> dict:
    r = client.put("/profile", json={"name": "Navin", "age": 21, "sex": "male", "height_cm": 175,
                                     "weight_kg": 70, "goal": "bulk", "activity": "moderate"})
    assert r.status_code == 200
    return r.json()
