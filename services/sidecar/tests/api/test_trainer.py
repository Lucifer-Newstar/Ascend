"""Trainer chat, feed and first-run state through the API (Ollama is off in tests)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.coach import ollama, runtime


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def test_the_screenshot_questions_get_relevant_different_answers(
    client: TestClient, profile: dict
) -> None:
    """1.0.0 answered all three with the same muscle tip (Coach page bug)."""
    hello = chat(client, "hello")
    can = chat(client, "what can you do")
    erase = chat(client, "none of this data is mine erase them all and start fresh")
    assert [hello["intent"], can["intent"], erase["intent"]] == ["greeting", "help", "erase"]
    assert len({hello["reply"], can["reply"], erase["reply"]}) == 3
    assert "Navin" in hello["reply"]
    assert all(r["fallback_reason"] is None for r in (hello, can, erase))


def test_same_questions_on_the_coach_page_are_routed(client: TestClient, profile: dict) -> None:
    tip = client.get("/coach/tip").json()["text"]
    for q in ("hello", "what can you do", "erase all my data and start fresh"):
        r = client.post("/coach/ask", json={"question": q}).json()
        assert r["text"] != tip and r["tip_code"].startswith("trainer:")


def test_routing_holds_when_the_model_times_out_or_is_rejected(
    client: TestClient, profile: dict, monkeypatch
) -> None:
    runtime._warm.clear()
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def slow(*a, **k):
        raise ollama.OllamaTimeout("cold")

    monkeypatch.setattr(ollama, "chat", slow)
    assert chat(client, "hello")["intent"] == "greeting"
    unknown = chat(client, "what's the meaning of life")
    assert unknown["fallback_reason"] == "timeout" and "took too long" in unknown["reply"]

    monkeypatch.setattr(ollama, "chat", lambda *a, **k: "Lift 999 kg tomorrow.")
    rejected = chat(client, "what's the meaning of life")
    assert rejected["fallback_reason"] == "guard_rejected"
    assert "999" not in rejected["reply"] and "safety check" in rejected["reply"]

    monkeypatch.setattr(ollama, "chat", lambda *a, **k: "Show up and keep going.")
    ok = chat(client, "what's the meaning of life")
    assert ok["source"] == "ollama" and ok["reply"] == "Show up and keep going."


def test_ai_off_everything_still_answers(client: TestClient, profile: dict) -> None:
    client.put("/settings", json={"ai_enabled": False})
    assert chat(client, "how do backups work")["faq_id"] == "backup"
    assert chat(client, "tour me through skills")["actions"][0] == {
        "kind": "tour",
        "target": "skills",
        "label": "Tour Skills",
    }
    unknown = chat(client, "what's the meaning of life")
    assert unknown["fallback_reason"] == "ai_disabled" and unknown["suggestions"]


def test_goal_check_through_the_trainer(client: TestClient, profile: dict) -> None:
    r = chat(client, "can I lose 10 kg in a month?")
    assert r["intent"] == "goal_check" and r["mood"] == "warning"
    assert "1% a week" in r["reply"]
    ok = chat(client, "I want to lose 3 kg in 2 months")
    assert ok["mood"] == "proud"


def test_state_and_onboarding(client: TestClient) -> None:
    s = client.get("/trainer/state").json()
    assert s == {
        "onboarded": False,
        "has_profile": False,
        "has_history": False,
        "demo_data": False,
        "trainer_id": "iskra",
        "tours_done": [],
    }
    client.put("/settings", json={"trainer_id": "vera"})
    s = client.put("/trainer/state", json={"onboarded": True, "tour_done": "app"}).json()
    assert s["onboarded"] and s["trainer_id"] == "vera" and s["tours_done"] == ["app"]
    assert client.put("/settings", json={"trainer_id": "nobody"}).status_code == 422


def test_feed_posts_each_event_once(client: TestClient, profile: dict, clock) -> None:
    from datetime import timedelta

    w = client.post("/workouts", json={}).json()
    ex = next(e for e in client.get("/exercises").json() if e["name"] == "Back Squat")
    client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": ex["id"], "reps": 5, "weight_kg": 100}
    )
    feed = client.get("/trainer/feed").json()
    kinds = [m["kind"] for m in feed["messages"]]
    assert "pr" in kinds and len(kinds) <= 3  # the shared daily cap (select-v1)
    pr = next(m for m in feed["messages"] if m["kind"] == "pr")
    assert pr["why"] == ["you set a new best estimated 1RM in the last 3 days"]
    unread = feed["unread"]
    assert client.get("/trainer/feed").json()["unread"] == unread  # not posted twice
    client.post("/trainer/feed/read", json={})
    assert client.get("/trainer/feed").json()["unread"] == 0
    clock.now += timedelta(days=6)
    kinds = [m["kind"] for m in client.get("/trainer/feed").json()["messages"]]
    assert "missed" in kinds


def test_kb_lists_questions(client: TestClient) -> None:
    kb = client.get("/trainer/kb").json()
    assert len(kb) >= 30 and {"id", "question", "section"} <= set(kb[0])


def test_selector_state_explain_and_why(client: TestClient, profile: dict) -> None:
    st = client.get("/selector/state").json()
    assert st["level"] == "beginner" and st["algo_version"] == "player-state-v1"
    ex = client.get("/selector/explain").json()
    assert ex["daily_cap"] == 3 and {i["id"] for i in ex["items"]} >= {"legs_under", "eat_enough"}
    blocked = {i["id"]: i["blocked_by"] for i in ex["items"]}
    assert blocked["expert_peaking"] == "level beginner"
    w = client.post("/workouts", json={}).json()
    ex_id = next(e for e in client.get("/exercises").json() if e["name"] == "Back Squat")["id"]
    client.post(
        f"/workouts/{w['id']}/sets", json={"exercise_id": ex_id, "reps": 5, "weight_kg": 60}
    )
    client.get("/trainer/feed")
    why = chat(client, "why?")
    assert why["intent"] == "why" and "because" in why["reply"]
    log = client.get("/selector/log").json()
    assert log and all(p["why"] for p in log)
