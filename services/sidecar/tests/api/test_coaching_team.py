"""Coaching team (item 13): the main trainer hands a coaching topic to its specialist."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.modules.trainer import team
from app.modules.trainer.schemas import ChatOut


def chat(client: TestClient, text: str) -> dict:
    r = client.post("/trainer/chat", json={"text": text})
    assert r.status_code == 200, r.text
    return r.json()


def reply(source: str = "knowledge", intent: str = "training_question", **kw: object) -> ChatOut:
    return ChatOut(reply="x", mood="neutral", intent=intent, source=source, **kw)  # type: ignore[arg-type]


# --- topic routing (keywords + the intent label) -----------------------------------------


@pytest.mark.parametrize(
    ("text", "label", "who"),
    [
        ("how do I increase my bench press PR", None, "idris"),
        ("best way to progress my deadlift and squat", None, "idris"),
        ("how do I get my first muscle-up", None, "dario"),
        ("tips for a longer handstand hold", None, "dario"),
        ("is running good for stamina", None, "kai"),
        ("how should I start muay thai footwork drills", None, "kai"),
        ("how do I improve hip mobility", None, "tara"),
        ("what should I do on a rest day when I'm sore", None, "tara"),
        ("how much protein in a banana shake", None, "vera"),
        ("is creatine worth taking for strength", "nutrition_question", "vera"),
        ("sharp pain in my shoulder during bench press", "injury_pain", "tara"),
    ],
)
def test_each_area_has_its_specialist(text: str, label: str | None, who: str) -> None:
    assert team.topic(text, label) == who


def test_no_clear_area_means_no_specialist() -> None:
    assert team.topic("what is the meaning of life") is None
    # A tie between two areas with no label to break it: the main trainer keeps it.
    assert team.topic("protein after running") is None


def test_a_named_specialist_takes_the_question() -> None:
    assert team.addressed("Kai, how long should I run?") == "kai"
    assert team.addressed("ask Vera about breakfast") == "vera"
    assert team.addressed("@dario what next") == "dario"
    assert team.addressed("karate kid") is None
    out = reply()
    assert team.specialist_for("Tara, how do I do a deadlift?", out) == "tara"


def test_app_help_greetings_and_cards_stay_with_the_main_trainer() -> None:
    assert team.specialist_for("how much protein", reply(source="rules", intent="help")) is None
    assert (
        team.specialist_for("log my meal", reply(source="faq", intent="faq", faq_id="log_meal"))
        is None
    )
    card = reply(source="rules", intent="action", proposal={"id": 1})
    assert team.specialist_for("2 eggs for breakfast", card) is None


def test_coaching_help_notes_go_to_their_owner() -> None:
    assert team.specialist_for("x", reply(source="faq", intent="faq", faq_id="protein")) == "vera"
    assert team.specialist_for("x", reply(source="faq", intent="faq", faq_id="sore")) == "tara"
    assert (
        team.specialist_for("x", reply(source="faq", intent="faq", faq_id="first_pullup"))
        == "dario"
    )
    assert team.specialist_for("x", reply(source="faq", intent="faq", faq_id="rpe")) == "idris"
    assert (
        team.specialist_for("x", reply(source="faq", intent="faq", faq_id="cardio_or_weights"))
        == "kai"
    )


def test_every_owner_and_area_is_a_real_trainer() -> None:
    assert set(team.AREAS) == {"idris", "dario", "kai", "tara", "vera"}
    assert set(team.FAQ_OWNER.values()) <= set(team.AREAS)
    from app.modules.trainer import kb

    ids = {e.id for e in kb.ENTRIES}
    assert set(team.FAQ_OWNER) <= ids


# --- the chat endpoint -------------------------------------------------------------------


def test_a_specialist_answers_with_a_handoff_line(client: TestClient, profile: dict) -> None:
    r = chat(client, "is creatine worth taking for strength")
    assert r["source"] == "knowledge"
    assert r["speaker"] == "vera"
    assert r["handoff"] == "That's Vera's area (nutrition). Over to her."
    # The words and the sources are the knowledge base's, unchanged by the handoff.
    assert "Creatine" in r["reply"] and r["citations"]


def test_pain_goes_to_tara_and_keeps_the_safety_line(client: TestClient, profile: dict) -> None:
    r = chat(client, "sharp pain in my shoulder during bench press")
    assert r["speaker"] == "tara" and r["handoff"].startswith("That's Tara's area")
    assert r["reply"].startswith("If it hurts, stop")


def test_a_help_note_in_an_area_is_answered_by_its_specialist(
    client: TestClient, profile: dict
) -> None:
    r = chat(client, "How much protein should I eat?")
    assert r["source"] == "faq" and r["faq_id"] == "protein"
    assert r["speaker"] == "vera" and r["handoff"]


def test_the_main_trainer_keeps_app_questions_and_greetings(
    client: TestClient, profile: dict
) -> None:
    for text in ("hello", "How does XP work?", "Give me a tour"):
        r = chat(client, text)
        assert r["speaker"] == "iskra" and r["handoff"] is None, text


def test_logging_cards_stay_with_the_main_trainer(client: TestClient, profile: dict) -> None:
    r = chat(client, "bench 60x5")
    assert r["intent"] == "action" and r["proposal"] is not None
    assert r["speaker"] == "iskra" and r["handoff"] is None


def test_a_chosen_main_trainer_runs_the_chat(client: TestClient, profile: dict) -> None:
    assert client.put("/settings", json={"trainer_id": "kai"}).status_code == 200
    assert chat(client, "hello")["speaker"] == "kai"
    # Nutrition still goes to Vera, and Kai is the one handing over.
    r = chat(client, "is creatine worth taking for strength")
    assert r["speaker"] == "vera" and r["handoff"]


def test_no_handoff_when_the_main_trainer_is_the_specialist(
    client: TestClient, profile: dict
) -> None:
    assert client.put("/settings", json={"trainer_id": "vera"}).status_code == 200
    r = chat(client, "is creatine worth taking for strength")
    assert r["speaker"] == "vera" and r["handoff"] is None


def test_the_team_can_be_switched_off(client: TestClient, profile: dict) -> None:
    s = client.get("/settings").json()
    assert s["team_handoff"] is True and s["trainer_id"] == "iskra"
    assert client.put("/settings", json={"team_handoff": False}).json()["team_handoff"] is False
    r = chat(client, "is creatine worth taking for strength")
    assert r["speaker"] == "iskra" and r["handoff"] is None


def test_changing_the_main_trainer_in_chat_is_a_card(client: TestClient, profile: dict) -> None:
    r = chat(client, "make dario my main trainer")
    assert r["proposal"] is not None
    assert "main trainer" in r["reply"].lower() or "main trainer" in str(r["proposal"]).lower()
    # Nothing changes until the card is confirmed.
    assert client.get("/settings").json()["trainer_id"] == "iskra"


def test_switching_the_team_off_in_chat_is_a_card(client: TestClient, profile: dict) -> None:
    r = chat(client, "turn off the coaching team")
    assert r["proposal"] is not None
    assert client.get("/settings").json()["team_handoff"] is True
