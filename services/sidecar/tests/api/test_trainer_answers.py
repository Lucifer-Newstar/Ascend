"""trainer-answers-v1: coach-style answers, honest "not sure" replies, one clarifying
question, and every safety rule kept (Ollama is off in tests)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def test_knowledge_answers_lead_with_the_answer_not_a_pasted_paragraph(
    client: TestClient, profile: dict
) -> None:
    r = chat(client, "What is tabata? How effective is it?")
    assert r["source"] == "knowledge" and r["citations"]
    assert "Here's what I have on that" not in r["reply"]
    assert "8 rounds of 20 seconds" in r["reply"]
    assert len(r["reply"].split()) < 110


def test_exercise_answers_are_numbered_steps(client: TestClient, profile: dict) -> None:
    r = chat(client, "what are the steps for a side plank?")
    assert r["citations"][0]["passage_id"] == "lib:dario:side-plank"
    assert "step by step" in r["reply"] and "\n1. " in r["reply"]
    assert "Also called" not in r["reply"]


def test_a_better_passage_beats_a_help_note_matched_on_one_word(
    client: TestClient, profile: dict
) -> None:
    """ "Should I stretch after exercise?" used to get the after-workout food note."""
    r = chat(client, "Should I stretch after exercise?")
    assert r["source"] == "knowledge"
    assert (
        r["citations"][0]["passage_id"]
        == "note:training_basics:stretching-before-or-after-exercise"
    )


def test_a_curated_help_note_keeps_its_own_question(client: TestClient, profile: dict) -> None:
    r = chat(client, "what should I eat to gain weight")
    assert r["source"] == "faq" and r["faq_id"] == "gain_weight"


def test_unsure_retrieval_offers_the_closest_note_and_asks(
    client: TestClient, profile: dict
) -> None:
    r = chat(client, "I have extremely bad posture, what can I do?")
    assert r["reply"].startswith("I'm not sure I have exactly that")
    assert '"Posture"' in r["reply"] and r["reply"].count("?") >= 1
    assert r["suggestions"] and r["citations"]


def test_a_statement_is_not_offered_a_neighbouring_note(client: TestClient, profile: dict) -> None:
    r = chat(client, "I have no bench")
    assert "closest note" not in r["reply"]


def test_a_vague_question_gets_one_clarifying_question(client: TestClient, profile: dict) -> None:
    r = chat(client, "which workout is the best?")
    assert r["intent"] == "clarify" and r["reply"].count("?") == 1
    assert "building muscle" in r["reply"]  # the goal on file (bulk)
    assert r["suggestions"][0] == "How do I build muscle?"
    assert r["proposal"] is None and not r["citations"]


def test_pain_keeps_the_doctor_line_on_every_path(client: TestClient, profile: dict) -> None:
    for q in (
        "I'm currently injured. Can I break 18 minutes for a 5K during cross country?",
        "my knee hurts when i squat",
    ):
        r = chat(client, q)
        assert "doctor" in r["reply"] or "physio" in r["reply"], (q, r["reply"])


def test_answers_use_the_profile_and_never_log_anything(client: TestClient, profile: dict) -> None:
    r = chat(client, "How much protein should I eat on off-days?")
    assert r["proposal"] is None
    r = chat(client, "Gaining weight without gaining fat")
    assert "your goal (bulk)" in r["reply"]
