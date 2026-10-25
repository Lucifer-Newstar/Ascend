"""v1.3 wave 2: the trainer edits your profile, kit, settings and plan (confirm + undo)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PROFILE = {
    "name": "Navin", "age": 21, "sex": "male", "height_cm": 170, "weight_kg": 42,
    "goal": "maintain", "activity": "moderate", "equipment": ["dumbbells", "rings"],
}  # fmt: skip


@pytest.fixture
def me(client: TestClient) -> TestClient:
    assert client.put("/profile", json=PROFILE).status_code == 200
    return client


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def card(client: TestClient, text: str) -> dict:
    p = chat(client, text)["proposal"]
    assert p is not None, text
    return p


def confirm(client: TestClient, p: dict) -> dict:
    r = client.post(f"/actions/{p['id']}/confirm", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "executed", r.json()
    return r.json()


def undo(client: TestClient, p: dict) -> None:
    r = client.post(f"/actions/{p['id']}/undo")
    assert r.status_code == 200 and r.json()["status"] == "undone", r.text


def test_profile_edits_confirm_and_undo(me: TestClient) -> None:
    p = card(me, "change my goal to bulk")
    assert p["kind"] == "update_profile" and "from maintain to bulk" in p["summary"][0]
    assert me.get("/profile").json()["goal"] == "maintain"  # nothing before confirm
    confirm(me, p)
    assert me.get("/profile").json()["goal"] == "bulk"
    undo(me, p)
    assert me.get("/profile").json()["goal"] == "maintain"
    for text, field, value in (
        ("set my age to 22", "age", 22),
        ("my height is 5'7", "height_cm", 170.2),
        ("I want to reach 50 kg", "target_weight_kg", 50),
        ("i'm a beginner", "experience", "beginner"),
        ("call me Navi", "name", "Navi"),
    ):
        confirm(me, card(me, text))
        assert me.get("/profile").json()[field] == value, text


def test_an_impossible_profile_value_is_refused_in_words(me: TestClient) -> None:
    r = chat(me, "set my age to 9")
    assert r["proposal"] is None and "can't set your age" in r["reply"]


def test_kit_edits(me: TestClient) -> None:
    p = card(me, "I have a bench")
    assert p["kind"] == "set_equipment" and "dumbbells, rings, bench" in p["summary"][0]
    confirm(me, p)
    assert set(me.get("/profile").json()["equipment"]) == {"dumbbells", "rings", "bench"}
    confirm(me, card(me, "I don't have rings anymore"))
    assert set(me.get("/profile").json()["equipment"]) == {"dumbbells", "bench"}
    q = card(me, "i have no equipment")
    confirm(me, q)
    assert me.get("/profile").json()["equipment"] == ["none"]
    undo(me, q)
    assert set(me.get("/profile").json()["equipment"]) == {"dumbbells", "bench"}
    assert "already" in chat(me, "I have dumbbells")["reply"]


def test_settings_edits(me: TestClient) -> None:
    for text, key, value in (
        ("switch to lbs", "units", "imperial"),
        ("dark mode", "theme", "dark"),
        ("turn off reminders", "reminders", False),
        ("switch trainer to vera", "trainer_id", "vera"),
        ("hide calories", "hide_calories", True),
    ):
        p = card(me, text)
        assert p["kind"] == "update_setting", text
        confirm(me, p)
        assert me.get("/settings").json()[key] == value, text
    p = card(me, "use kg")
    confirm(me, p)
    undo(me, p)
    assert me.get("/settings").json()["units"] == "imperial"


def test_a_locked_theme_stays_locked(me: TestClient) -> None:
    r = chat(me, "switch to frost theme")
    assert r["proposal"] is None and "Frost theme is still locked" in r["reply"]
    assert "Reach rank D" in r["reply"]
    confirm(me, card(me, "light mode"))
    assert me.get("/settings").json()["theme"] == "light"


def _follow(client: TestClient, key: str) -> None:
    assert client.put("/plans/current", json={"program_key": key}).status_code == 200


def _plan_moves(client: TestClient) -> set[str]:
    return {i["exercise"] for d in client.get("/plans/current").json()["days"] for i in d["items"]}


def test_editing_a_built_in_plan_saves_your_own_copy(me: TestClient, clock) -> None:
    _follow(me, "ppl_6")  # no bench: the plan shows the floor press, and edits start there
    before = me.get("/plans/current").json()
    p = card(me, "swap dumbbell floor press for push-ups")
    assert p["kind"] == "edit_plan" and "your own copy" in " ".join(p["summary"])
    confirm(me, p)
    now = me.get("/plans/current").json()
    assert now["program_key"].startswith("custom-") and "(my version)" in now["name"]
    assert "Push-up" in _plan_moves(me) and "Dumbbell Floor Press" not in _plan_moves(me)
    assert now["started_on"] == before["started_on"]
    undo(me, p)
    assert me.get("/plans/current").json()["program_key"] == "ppl_6"


def test_editing_your_own_plan_changes_it_in_place(me: TestClient) -> None:
    _follow(me, "ppl_6")
    confirm(me, card(me, "swap dumbbell floor press for push-ups"))
    key = me.get("/plans/current").json()["program_key"]
    p = card(me, "make push-ups 5 sets")
    confirm(me, p)
    assert me.get("/plans/current").json()["program_key"] == key
    sets = {i["sets"] for d in me.get("/plans/current").json()["days"] for i in d["items"]
            if i["exercise"] == "Push-up"}  # fmt: skip
    assert sets == {5}
    undo(me, p)
    confirm(me, card(me, "remove push-ups from my plan"))
    assert "Push-up" not in _plan_moves(me)
    confirm(me, card(me, "add 3 sets of plank to my plan"))
    assert "Plank" in _plan_moves(me)


def _rests(client: TestClient, move: str) -> list[int]:
    days = client.get("/plans/current").json()["days"]
    return [i["rest_s"] for d in days for i in d["items"] if i["exercise"] == move]


def test_rest_between_sets(me: TestClient) -> None:
    _follow(me, "ppl_6")
    confirm(me, card(me, "swap dumbbell floor press for push-ups"))
    before = _rests(me, "Push-up")
    p = card(me, "rest 75 seconds between sets of push-ups")
    assert p["kind"] == "edit_plan" and "rest 75 s between sets" in p["summary"][0]
    confirm(me, p)
    assert set(_rests(me, "Push-up")) == {75}
    undo(me, p)
    assert _rests(me, "Push-up") == before


def test_days_per_week(me: TestClient) -> None:
    p = card(me, "I can train 4 days a week")
    assert p["kind"] == "update_setting" and "from 3 to 4" in p["summary"][0]
    confirm(me, p)
    assert me.get("/settings").json()["sessions_per_week"] == 4
    undo(me, p)
    assert me.get("/settings").json()["sessions_per_week"] == 3


def test_moving_a_day(me: TestClient) -> None:
    _follow(me, "bodyweight_starter_3")
    days = {d["weekday"] for d in me.get("/plans/current").json()["days"]}
    free = next(w for w in range(7) if w not in days)
    first = min(days)
    names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    confirm(me, card(me, f"move {names[first]} to {names[free]}"))
    moved = {d["weekday"] for d in me.get("/plans/current").json()["days"]}
    assert free in moved and first not in moved


def test_plan_edit_errors_are_plain(me: TestClient) -> None:
    assert "don't follow a program" in chat(me, "swap squats for lunges")["reply"]
    _follow(me, "bodyweight_starter_3")
    assert "isn't in" in chat(me, "remove deadlift from my plan")["reply"]


def test_questions_are_not_edits(me: TestClient) -> None:
    for text in ("what is my goal?", "how do i change my theme", "should I switch to lbs?"):
        assert chat(me, text)["proposal"] is None, text


def test_get_profile_returns_experience(client: TestClient) -> None:
    """GET /profile left experience out, so a page saving the profile it had read reset it."""
    r = client.put("/profile", json={**PROFILE, "experience": "intermediate"})
    assert r.status_code == 200 and r.json()["experience"] == "intermediate"
    echo = client.get("/profile").json()
    assert client.put("/profile", json=echo).json()["experience"] == "intermediate"


def test_all_six_kit_choices_fit_on_the_profile(client: TestClient) -> None:
    kit = ["none", "pullup_bar", "rings", "dumbbells", "bench", "gym"]
    assert client.put("/profile", json={**PROFILE, "equipment": kit}).status_code == 200
