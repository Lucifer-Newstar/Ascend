"""In-app actions: propose -> confirm -> undo, the allowlist, the audit log, the chat card."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.modules.coach import ollama


def test_log_set_from_chat_needs_confirm_and_can_be_undone(client: TestClient, profile) -> None:
    r = client.post("/trainer/chat", json={"text": "log 3x10 bench at 60 kg"}).json()
    card = r["proposal"]
    assert r["intent"] == "action" and card["status"] == "proposed"
    assert card["summary"] == ["Log 3 \u00d7 10 Barbell Bench Press, 60 kg, in today's session."]
    assert client.get("/workouts").json() == []  # nothing ran yet
    done = client.post(f"/actions/{card['id']}/confirm", json={}).json()
    assert done["status"] == "executed" and len(done["result"]["set_ids"]) == 3 and done["undoable"]
    w = client.get("/workouts/active").json()
    assert len(w["sets"]) == 3
    assert client.post(f"/actions/{card['id']}/confirm", json={}).status_code == 409
    undone = client.post(f"/actions/{card['id']}/undo", json={}).json()
    assert undone["status"] == "undone"
    assert client.get("/workouts/active").json()["sets"] == []
    log = client.get("/actions/log").json()
    assert log[0]["id"] == card["id"] and log[0]["origin_text"] == "log 3x10 bench at 60 kg"


def test_bare_log_lines_in_chat_are_proposals_not_help_notes(
    client: TestClient, profile, monkeypatch
) -> None:
    """The command bar's grammar holds in the chat too ("weight 81.4" used to get the
    weigh-in help note); such lines are matched by rules only, never sent to the model."""

    def no_model(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("the model was asked to parse a bare log line")

    monkeypatch.setattr(ollama, "chat", no_model)
    for text, kind in (("weight 81.4", "log_weight"), ("bench 80x5 @8", "log_set")):
        r = client.post("/trainer/chat", json={"text": text}).json()
        assert r["intent"] == "action" and r["proposal"]["kind"] == kind, text
    faq = client.post("/trainer/chat", json={"text": "how do I log a weigh-in?"}).json()
    assert faq["proposal"] is None


def test_weigh_in_meal_and_program(client: TestClient, profile) -> None:
    p = client.post("/actions/parse", json={"text": "i weigh 71.2 kg"}).json()["proposal"]
    client.post(f"/actions/{p['id']}/confirm", json={})
    assert client.get("/body-metrics").json()[0]["weight_kg"] == 71.2
    client.post(f"/actions/{p['id']}/undo", json={})
    assert client.get("/body-metrics").json() == []
    m = client.post("/actions/parse", json={"text": "i ate 2 idli for breakfast"}).json()
    assert m["proposal"]["summary"][0].startswith("Log 2 \u00d7 Idli")
    done = client.post(f"/actions/{m['proposal']['id']}/confirm", json={}).json()
    assert done["status"] == "executed"
    f = client.post("/actions/parse", json={"text": "switch me to PPL"}).json()["proposal"]
    assert "Push / pull / legs" in f["summary"][0]
    client.post(f"/actions/{f['id']}/confirm", json={})
    assert client.get("/plans/current").json()["program_key"] == "ppl_6"
    client.post(f"/actions/{f['id']}/undo", json={})
    assert client.get("/plans/current").status_code == 404


def test_unknown_names_and_non_actions(client: TestClient, profile) -> None:
    r = client.post("/actions/parse", json={"text": "log 3x10 zorblax at 60 kg"}).json()
    assert r["proposal"] is None and "zorblax" in r["error"]
    assert client.post("/actions/parse", json={"text": "what is xp"}).json() == {
        "proposal": None,
        "error": None,
    }
    assert client.post("/actions", json={"kind": "drop_tables", "params": {}}).status_code == 422


def test_erase_needs_the_word(client: TestClient, profile) -> None:
    r = client.post("/trainer/chat", json={"text": "erase everything and start fresh"}).json()
    card = r["proposal"]
    assert card["kind"] == "erase_data" and card["confirm_word"] == "ERASE"
    assert client.post(f"/actions/{card['id']}/confirm", json={"typed": "yes"}).status_code == 409
    assert client.get("/profile").status_code == 200
    done = client.post(f"/actions/{card['id']}/confirm", json={"typed": "erase"}).json()
    assert done["status"] == "executed" and not done["undoable"]
    assert client.get("/profile").status_code == 404
    assert [a["kind"] for a in client.get("/actions/log").json()] == ["erase_data"]


def test_cancel_and_auto_allow(client: TestClient, profile) -> None:
    p = client.post("/actions/parse", json={"text": "weight 70"}).json()["proposal"]
    assert client.post(f"/actions/{p['id']}/cancel", json={}).json()["status"] == "cancelled"
    assert (
        client.put("/actions/auto", json={"kind": "erase_data", "allow": True}).status_code == 409
    )
    kinds = client.put("/actions/auto", json={"kind": "log_weight", "allow": True}).json()
    assert next(k for k in kinds if k["kind"] == "log_weight")["auto_ok"] is True
    p2 = client.post("/actions/parse", json={"text": "weight 70"}).json()["proposal"]
    assert p2["auto_ok"] is True and p2["status"] == "proposed"  # still needs the confirm call


def test_ai_parse_is_validated_and_number_guarded(client: TestClient, profile, monkeypatch) -> None:
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    reply = {"kind": "log_weight", "params": {"weight_kg": 70.5}}
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: json.dumps(reply))
    r = client.post("/actions/parse", json={"text": "put my scale reading of 70.5 in"}).json()
    assert r["proposal"]["kind"] == "log_weight" and r["proposal"]["source"] == "ai"
    reply["params"] = {"weight_kg": 99.0}  # a number the user never wrote
    assert (
        client.post("/actions/parse", json={"text": "put my scale reading of 70.5 in"}).json()[
            "proposal"
        ]
        is None
    )
    reply.update(kind="erase_data", params={})  # never via the model
    assert (
        client.post("/actions/parse", json={"text": "make it all go away"}).json()["proposal"]
        is None
    )
