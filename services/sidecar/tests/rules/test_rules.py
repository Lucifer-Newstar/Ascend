"""The checkable rules in docs/RULES_AND_BASELINE.md (R-numbers match the doc).

These tests exist so that a later feature cannot quietly break a rule the team agreed
on. If one fails, the change is either a bug or a rule change: a rule change goes to
Navin first and the doc is updated in the same pull request.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.modules.gamification.streaks import compute_streak

MON = date(2026, 11, 2)

# B1/B2 in the doc: the trainer battery must not get worse than this.
HARNESS_MIN_PASS = 251
HARNESS_MAX_FAIL = 1


def _push_up(client: TestClient) -> int:
    return next(
        e["id"] for e in client.get("/exercises", params={"q": "Push-up"}).json()
        if e["name"] == "Push-up"
    )  # fmt: skip


def test_r1_only_training_keeps_the_streak(client: TestClient, profile) -> None:
    """R1: a meal, a weigh-in or a quest tick earns XP but never keeps the streak."""
    client.post("/body-metrics", json={"weight_kg": 42})
    s = client.get("/game/summary").json()["streak"]
    assert s["active_today"] is False and s["current"] == 0
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": _push_up(client), "reps": 10})
    assert client.get("/game/summary").json()["streak"]["active_today"] is True


def test_r2_planned_rest_days_are_neutral() -> None:
    """R2: a Mon/Wed/Fri plan keeps a growing streak across its rest days."""
    trained = [MON + timedelta(days=o) for o in (0, 2, 4, 7, 9, 11)]
    rest = [MON + timedelta(days=o) for o in (1, 3, 5, 6, 8, 10)]
    assert compute_streak(trained, MON + timedelta(days=11), rest_days=rest).current == 6


def test_r3_the_trainer_never_writes_before_confirm(client: TestClient, profile) -> None:
    """R3: chat lines that change data only ever come back as a proposal."""
    before = client.get("/workouts").json()
    for line in ("10 pushups", "I'm 44 kg today", "2 idli for breakfast", "dark mode",
                 "change my goal to bulk", "I have a bench"):  # fmt: skip
        r = client.post("/trainer/chat", json={"text": line}).json()
        assert r["proposal"] is None or r["proposal"]["status"] == "proposed", line
    assert client.get("/workouts").json() == before
    assert client.get("/settings").json()["theme"] != "dark"
    assert client.get("/profile").json()["goal"] == profile["goal"]


def test_r4_yes_never_erases_and_scoped_deletes_never_offer_erase(
    client: TestClient, profile
) -> None:
    """R4: erasing everything needs its word typed; "remove all meals" is not an erase."""
    r = client.post("/trainer/chat", json={"text": "remove all meals"}).json()
    assert r["proposal"] is None or r["proposal"]["kind"] != "erase_data"
    r = client.post("/trainer/chat", json={"text": "erase all my data"}).json()
    p = r["proposal"]
    assert p is not None and p["kind"] == "erase_data" and p["confirm_word"]
    client.post("/trainer/chat", json={"text": "yes"})
    assert client.post(f"/actions/{p['id']}/confirm", json={}).status_code >= 400
    log = {a["id"]: a["status"] for a in client.get("/actions/log").json()}
    assert log[p["id"]] != "executed"
    assert client.get("/profile").status_code == 200


def test_r5_every_trainer_edit_can_be_undone(client: TestClient, profile) -> None:
    """R5: propose -> confirm -> undo for the edit actions."""
    p = client.post("/trainer/chat", json={"text": "switch to lbs"}).json()["proposal"]
    done = client.post(f"/actions/{p['id']}/confirm", json={}).json()
    assert done["status"] == "executed" and done["undoable"] is True
    assert client.post(f"/actions/{p['id']}/undo").json()["status"] == "undone"
    assert client.get("/settings").json()["units"] == "metric"


def test_b1_the_trainer_battery_does_not_get_worse() -> None:
    """B1/B2: the 343-message battery (rules only) stays at or above the baseline."""
    from collections import Counter

    from eval import trainer_chat

    rows = trainer_chat.run()
    tally = Counter(r["verdict"] for r in rows)
    assert tally[True] >= HARNESS_MIN_PASS, tally
    assert tally[False] <= HARNESS_MAX_FAIL, [r["text"] for r in rows if r["verdict"] is False]
