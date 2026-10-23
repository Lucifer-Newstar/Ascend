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


@pytest.fixture(autouse=True)
def _no_local_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never depend on a local model server being installed on the machine: "installed"
    follows the fakes the AI tests patch in (`ollama.server_info` / `ollama.is_available`);
    on the closed test port it is False."""
    from app.modules.coach import ollama
    from app.modules.progress import service as progress_service

    def installed() -> bool:
        version, models = ollama.server_info("http://127.0.0.1:9", timeout=0.2)
        return bool(version and models) or ollama.is_available(
            "http://127.0.0.1:9", "probe", timeout=0.2
        )

    monkeypatch.setattr(progress_service, "local_ai_installed", installed)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 10, 20, 9, 0, 0))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Point Ollama at a closed port so the coach always takes the rules path in tests.
    return Settings(
        data_dir=tmp_path,
        db_url=f"sqlite:///{tmp_path / 'test.db'}",
        token=TOKEN,
        ollama_host="http://127.0.0.1:9",
    )


@pytest.fixture
def client(settings: Settings, clock: FakeClock) -> TestClient:
    # Real Alembic migrations; the outbox worker is off so tests drive it explicitly.
    app = create_app(settings, clock=clock, outbox_interval=0)
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as c:
        yield c


@pytest.fixture
def profile(client: TestClient) -> dict:
    r = client.put(
        "/profile",
        json={
            "name": "Navin",
            "age": 21,
            "sex": "male",
            "height_cm": 175,
            "weight_kg": 70,
            "goal": "bulk",
            "activity": "moderate",
        },
    )
    assert r.status_code == 200
    return r.json()
