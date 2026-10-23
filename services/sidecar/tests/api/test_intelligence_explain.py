"""Explanations: the local model may phrase a number's "why", but the coach guard checks
every number against the facts, and any failure shows the template instead."""

from datetime import timedelta

import pytest

from app.modules.coach import ollama
from app.modules.intelligence import explain
from tests.api.test_intelligence_progression import session
from tests.api.test_workouts import exercise_id


@pytest.fixture(autouse=True)
def fresh_cache():
    explain.clear_cache()
    yield
    explain.clear_cache()


def model(monkeypatch, reply: str | Exception) -> list[dict]:
    calls: list[dict] = []
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def fake_chat(host, model, facts, question, timeout=20.0, system=ollama.SYSTEM_PROMPT):
        calls.append({"facts": facts, "question": question, "system": system})
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(ollama, "chat", fake_chat)
    return calls


def bench_target(client, clock) -> int:
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 10, 8)] * 3)
    return bench


def test_model_sentence_with_only_fact_numbers_is_shown(client, profile, clock, monkeypatch):
    calls = model(
        monkeypatch, "You hit all 10 reps, so add 2.5 kg and drop back to 6 reps at RPE 8."
    )
    bench = bench_target(client, clock)
    e = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert e["phrasing"] == "model" and e["fallback"] is None
    assert e["checks"]["numbers"] == "pass"
    assert e["template"].startswith("Every set hit 10 reps")
    assert "target load kg: 62.5" in calls[0]["facts"]
    assert calls[0]["system"] == explain.SYSTEM_PROMPT
    # cached: the second request does not call the model again
    client.get(f"/intelligence/progression/{bench}/explanation")
    assert len(calls) == 1


def test_an_invented_number_falls_back_to_the_template(client, profile, clock, monkeypatch):
    model(monkeypatch, "Great work, add 5 kg next time for 8 reps.")
    bench = bench_target(client, clock)
    e = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert e["phrasing"] == "template" and e["fallback"] == "check_failed: numbers"
    assert e["text"] == e["template"]


def test_banned_phrases_fall_back_too(client, profile, clock, monkeypatch):
    model(monkeypatch, "I changed your plan: 62.5 kg for 6 reps.")
    bench = bench_target(client, clock)
    e = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert e["phrasing"] == "template" and e["fallback"].startswith("check_failed")


def test_model_down_or_ai_off_uses_the_template(client, profile, clock, monkeypatch):
    client.put("/settings", json={"ai_enabled": True})  # switched on, model not running
    bench = bench_target(client, clock)
    # conftest points the model host at a closed port
    e = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert (e["phrasing"], e["fallback"]) == ("template", "model_unavailable")
    model(monkeypatch, ollama.OllamaUnavailable("timeout"))
    explain.clear_cache()
    e2 = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert e2["fallback"] == "model_error: timeout"
    client.put("/settings", json={"ai_enabled": False})
    e3 = client.get(f"/intelligence/progression/{bench}/explanation").json()
    assert e3["fallback"] == "ai_disabled"


def test_muscle_readiness_explanation(client, profile, clock, monkeypatch):
    bench = exercise_id(client, "Barbell Bench Press")
    session(client, clock, bench, [(60, 8, 9)] * 3, days_later=0.5)
    e = client.get("/intelligence/recovery/pec_major_sternal/explanation").json()
    assert e["phrasing"] == "template"
    assert (
        e["text"].startswith("Mid and lower chest is ") and "effective sets of fatigue" in e["text"]
    )
    assert "readiness pct:" in e["facts"]
    assert client.get("/intelligence/recovery/elbows/explanation").status_code == 404
    clock.now += timedelta(days=30)
    rested = client.get("/intelligence/recovery/pec_major_sternal/explanation").json()
    assert "100% ready" in rested["text"] or "fully recovered" in rested["text"]
