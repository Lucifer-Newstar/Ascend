"""v1.4: the game runs on the PC's local clock (Navin, 2026-10-25).

The sidecar's clock is the local wall clock (`datetime.now()`, no time zone), so a week,
a season and a day turn over at local midnight. These tests move a fake local clock over
the boundaries; a UTC clock would turn them over 5.5 hours late in India.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.modules.gamification import boss


def test_the_seasonal_boss_changes_at_local_midnight(client: TestClient, profile, clock) -> None:
    clock.now = datetime(2026, 12, 6, 23, 55)  # Sunday night, the last Harvest week
    b = client.get("/game/boss").json()
    assert b["week_start"] == "2026-11-30" and b["name"] == "Harvest Colossus"
    clock.now = datetime(2026, 12, 7, 0, 5)  # ten minutes later: Monday, Winter begins
    b = client.get("/game/boss").json()
    assert b["week_start"] == "2026-12-07" and b["name"] == "Winter Wraith"
    assert b["season"] == "Winter" and b["season_ends"] == "2027-02-28"


def test_a_session_just_before_local_midnight_counts_for_that_day(
    client: TestClient, profile, clock
) -> None:
    clock.now = datetime(2026, 10, 25, 23, 50)  # Sunday 23:50 local
    p = client.post("/trainer/chat", json={"text": "10 pushups"}).json()["proposal"]
    assert client.post(f"/actions/{p['id']}/confirm", json={}).status_code == 200
    clock.now = datetime(2026, 10, 26, 0, 10)  # Monday 00:10: a new week
    g = client.get("/game/summary").json()
    assert g["streak"]["lifetime_sessions"] == 1
    sessions = client.get("/workouts").json()
    assert sessions and sessions[0]["started_at"].startswith("2026-10-25")


def _catalog_ids() -> set[str] | None:
    for parent in Path(__file__).resolve().parents:
        f = parent / "apps/desktop/src/lib/cosmetics.ts"
        if f.is_file():
            return set(re.findall(r'id: "([a-z0-9_]+)"', f.read_text("utf-8")))
    return None


def test_every_seasonal_drop_is_a_real_cosmetic() -> None:
    ids = _catalog_ids()
    if ids is None:
        pytest.skip("no apps/desktop in this checkout")
    assert {s.drop for s in boss.SEASONS} <= ids
