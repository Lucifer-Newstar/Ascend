"""v1.4: the unlock log behind the Unlocks page (dates and replays)."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

DAGGER = {"key": "cosmetic:weapon_shadow_dagger", "kind": "cosmetic", "title": "Shadow Dagger"}
GOLEM = {
    "key": "boss:Iron Golem",
    "kind": "boss",
    "title": "Golem Breaker",
    "detail": "Beat the Iron Golem",
}
RANK_D = {"key": "rank:D", "kind": "rank", "title": "Rank D"}


def sync(client: TestClient, *items: dict) -> dict:
    r = client.post("/game/unlocks/sync", json={"items": list(items)})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_first_sync_is_quiet_then_new_unlocks_come_back(client: TestClient, clock) -> None:
    clock.now = datetime(2026, 10, 20, 9, 0)
    first = sync(client, DAGGER, GOLEM)
    assert first == {"new": [], "total": 2}  # an update does not replay old unlocks
    clock.now = datetime(2026, 10, 25, 18, 30)
    out = sync(client, DAGGER, GOLEM, RANK_D)
    assert [u["key"] for u in out["new"]] == ["rank:D"] and out["total"] == 3
    assert out["new"][0]["at"] == "2026-10-25T18:30:00" and out["new"][0]["seeded"] is False
    assert sync(client, DAGGER, GOLEM, RANK_D)["new"] == []  # each unlock plays once
    log = client.get("/game/unlocks").json()
    assert [u["key"] for u in log][0] == "rank:D"
    assert {u["key"]: u["seeded"] for u in log} == {
        "rank:D": False,
        "cosmetic:weapon_shadow_dagger": True,
        "boss:Iron Golem": True,
    }


def test_bad_unlocks_are_refused(client: TestClient) -> None:
    for bad in (
        {"key": "no-colon", "kind": "rank", "title": "x"},
        {"key": "rank:S", "kind": "money", "title": "x"},
        {"key": "rank:S", "kind": "rank", "title": ""},
        {"key": "rank:S", "kind": "rank", "title": "x", "extra": 1},
    ):
        assert client.post("/game/unlocks/sync", json={"items": [bad]}).status_code == 422, bad


def test_start_fresh_clears_the_unlock_log() -> None:
    from app.core import reset

    assert "unlock_events" not in reset.REFERENCE_TABLES  # it is the user's data
