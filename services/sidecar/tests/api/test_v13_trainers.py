"""v1.3: Tara and Idris join the roster (their art is in the desktop app)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_tara_and_idris_can_be_picked(client: TestClient) -> None:
    for tid in ("tara", "idris"):
        r = client.put("/settings", json={"trainer_id": tid})
        assert r.status_code == 200 and r.json()["trainer_id"] == tid
        assert client.get("/trainer/state").json()["trainer_id"] == tid


def test_an_unknown_trainer_is_refused(client: TestClient) -> None:
    assert client.put("/settings", json={"trainer_id": "zed"}).status_code == 422
