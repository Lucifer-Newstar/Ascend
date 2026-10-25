"""v1.4: the trainer builds your plan from what you tell it (planbuilder-v1).

Free-chat pickup is the main path; "Build my plan" is the optional interview. Everything
is a card: nothing is saved before confirm, and undo puts the old plan back.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PROFILE = {
    "name": "Navin", "age": 21, "sex": "male", "height_cm": 170, "weight_kg": 42,
    "goal": "bulk", "activity": "moderate", "equipment": ["rings"],
}  # fmt: skip


@pytest.fixture
def me(client: TestClient) -> TestClient:
    assert client.put("/profile", json=PROFILE).status_code == 200
    r = client.put("/plans/current", json={"program_key": "bodyweight_starter_3"})
    assert r.status_code == 200, r.text
    return client


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def confirm(client: TestClient, p: dict) -> dict:
    r = client.post(f"/actions/{p['id']}/confirm", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "executed", r.json()
    return r.json()


def current(client: TestClient) -> dict:
    return client.get("/plans/current").json()


def test_dumbbells_in_free_chat_become_a_plan_update_card(me: TestClient) -> None:
    before = current(me)["name"]
    out = chat(me, "I have an 8kg dumbbell and two 5kg")
    p = out["proposal"]
    assert p["kind"] == "build_plan"
    assert "update your plan" in out["reply"]
    summary = " ".join(p["summary"])
    assert "Remember: Dumbbells: 8 kg and 2 × 5 kg." in summary
    assert "Add to your equipment: dumbbells." in summary
    assert current(me)["name"] == before  # nothing before confirm (R3)
    confirm(me, p)
    plan = current(me)
    assert plan["name"] == "My plan"
    flat = [i["exercise"] for d in plan["days"] for i in d["items"]]
    assert "Dumbbell Squat" in flat and "Dumbbell Floor Press" in flat
    assert "dumbbells" in me.get("/profile").json()["equipment"]
    # Undo puts the old program, kit and schedule back (R5).
    assert me.post(f"/actions/{p['id']}/undo").json()["status"] == "undone"
    assert current(me)["name"] == before
    assert me.get("/profile").json()["equipment"] == ["rings"]
    assert me.get("/schedule").json()["source"] == "program"


def test_the_whole_story_in_free_chat(me: TestClient) -> None:
    for text in (
        "I have an 8kg dumbbell and two 5kg",
        "I have a punching bag, hand wraps and a gripper",
        "kickboxing and muay thai, trained 3 years ago, I can train 5 days a week",
        "I can't eat much but I can drink",
    ):
        p = chat(me, text)["proposal"]
        assert p is not None and p["kind"] == "build_plan", text
        confirm(me, p)
    plan = current(me)
    days = {d["weekday"]: d for d in plan["days"]}
    assert sorted(days) == [0, 1, 2, 4, 5], [(d["weekday"], d["name"]) for d in plan["days"]]
    assert days[1]["name"].startswith("Skill") and days[5]["name"].startswith("Skill")
    skill = [i["exercise"] for i in days[1]["items"]]
    assert "Heavy Bag Combos" in skill and "Roundhouse Kick Drill" in skill
    assert len(days) <= 5
    s = me.get("/schedule").json()
    assert s["source"] == "you" and 1 in s["days"] and 5 in s["days"]
    last = chat(me, "I want to train muay thai")["proposal"]
    text = " ".join(last["summary"])
    assert "Shake" in text and "oat" not in text.lower()
    assert "waist height" in text


def test_an_unhealthy_pace_is_said_plainly_with_realistic_targets(me: TestClient) -> None:
    out = chat(me, "my goal is 50 kg from 42 kg in a month")
    assert out["proposal"] is None
    assert "won't plan it" in out["reply"] and out["mood"] == "warning"
    assert out["suggestions"] == ["I want to reach 43 kg", "I want to reach 44 kg"]
    # A plain target stays the profile edit from v1.3.
    assert chat(me, "I want to reach 50 kg")["proposal"]["kind"] == "update_profile"


def test_build_my_plan_interview_with_chips(me: TestClient) -> None:
    out = chat(me, "Build my plan")
    assert out["intent"] == "plan_builder" and "Gain weight" in out["suggestions"]
    out = chat(me, "Gain weight")
    assert "42 kg to 50 kg" in out["reply"]
    out = chat(me, "42 kg to 50 kg")
    assert "16-32 weeks" in out["reply"]  # the realism check, then the next question
    out = chat(me, "8 kg dumbbell and two 5 kg, a punching bag and a gripper")
    assert "Muay Thai" in out["suggestions"]
    out = chat(me, "muay thai, 3 years ago")
    out = chat(me, "5 days")
    assert "appetite" in out["reply"]
    out = chat(me, "I can't eat much but I can drink")
    p = out["proposal"]
    assert p is not None and p["kind"] == "build_plan"
    summary = " ".join(p["summary"])
    assert "Target weight: 50 kg." in summary and "Muay Thai, last trained 3 years ago" in summary
    assert "Tue Skill" in summary and "Sat Skill" in summary
    confirm(me, p)
    assert current(me)["name"] == "My plan"


def test_the_interview_can_stop_and_skip(me: TestClient) -> None:
    chat(me, "build my plan")
    assert "didn't catch" in chat(me, "purple")["reply"]
    assert "Your weight now" in chat(me, "skip")["reply"]
    out = chat(me, "stop")
    assert out["reply"].startswith("Stopped")
    # Out of the interview, normal chat is back.
    assert chat(me, "10 pushups")["proposal"]["kind"] == "log_set"


def test_questions_and_no_profile(client: TestClient) -> None:
    assert chat(client, "how do I use a punching bag?").get("proposal") is None
    out = chat(client, "I have a punching bag")
    assert out["proposal"] is None and "profile first" in out["reply"]
