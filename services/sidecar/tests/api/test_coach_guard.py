"""The coach never shows a model reply that fails the validators (ADR-0011)."""

import pytest

from app.modules.coach import ollama


@pytest.fixture
def model(monkeypatch):
    """Pretend Ollama is up and answers with whatever the test sets."""
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    reply = {"text": ""}

    def fake_chat(host, model, facts, question, timeout=20.0, **kwargs):
        reply["facts"] = facts
        return reply["text"]

    monkeypatch.setattr(ollama, "chat", fake_chat)
    return reply


def test_an_invented_number_is_replaced_by_the_rules_tip(client, profile, model):
    model["text"] = "Eat 3,400 kcal today and add 6 sets of squats."
    r = client.post("/coach/ask", json={"question": "any advice for tonight?"}).json()
    assert r["source"] == "rules"
    assert r["fallback_reason"] == "guard_rejected"
    assert r["checks"]["numbers"] == "fail"
    assert "3,400" not in r["text"]


def test_numbers_from_the_facts_pass(client, profile, model):
    # The fresh profile's target appears in the facts the model receives.
    client.get("/coach/tip")
    target = next(
        line.split("estimated ")[1].split(" kcal")[0]
        for line in model["facts"].splitlines()
        if line.startswith("Calories")
    )
    model["text"] = f"Your target is {target} kcal; you haven't eaten yet."
    r = client.get("/coach/tip").json()
    assert r["source"] == "ollama"
    assert r["checks"]["numbers"] == "pass"


def test_numbers_from_the_question_pass(client, profile, model):
    model["text"] = "80 kg for 5 reps is a good top set."
    r = client.post("/coach/ask", json={"question": "I did 80 kg for 5 reps"}).json()
    assert r["source"] == "ollama"


def test_a_dose_is_never_shown(client, profile, model):
    model["text"] = "Take a painkiller before you train."
    r = client.post("/coach/ask", json={"question": "my knee feels odd"}).json()
    assert r["source"] == "rules"
    assert r["fallback_reason"] == "guard_rejected"
    assert r["checks"]["banned"] == "fail:medicine"


def test_small_counts_in_the_wording_pass(client, profile, model):
    model["text"] = "Two quick things: rest well, and keep 3 easy habits going."
    r = client.post("/coach/ask", json={"question": "any advice for tonight?"}).json()
    assert r["source"] == "ollama"
