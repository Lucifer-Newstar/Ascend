import json
import sqlite3

import httpx
import pytest

from app.modules.coach import ollama
from app.modules.workouts import custom


def analyze(client, name, **kw):
    r = client.post("/exercises/analyze", json={"name": name, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def body_from(a, **over):
    p = a["proposal"]
    body = {
        "name": a["name"],
        "section": p["section"],
        "equipment": p["equipment"],
        "measure": p["measure"],
        "pattern": p["pattern"],
        "difficulty": p["difficulty"],
        "muscles": p["muscles"],
        "rep_low": p["rep_low"],
        "rep_high": p["rep_high"],
        "instructions": p["instructions"],
        "aliases": p["aliases"],
        "field_sources": a["field_sources"],
        "attribution": a["attribution"],
    }
    body.update(over)
    return body


@pytest.fixture
def no_ai(client):
    client.put("/settings", json={"ai_enabled": False})


def test_rules_only_proposal_with_every_source_named(client, no_ai):
    a = analyze(client, "Banded Pallof Hold")
    p = a["proposal"]
    assert (p["equipment"], p["measure"], p["section"]) == ("band", "hold", "gym")
    assert {m["muscle"]: m["weight"] for m in p["muscles"]}["obliques"] == 1.0
    assert a["ai"]["status"] == "off" and a["online"]["status"] == "off"
    assert set(a["field_sources"].values()) == {"rules"}
    assert {"section", "equipment", "measure", "muscles"} <= set(a["field_sources"])


def test_library_matches_and_duplicates(client, no_ai):
    a = analyze(client, "pullups")
    assert a["duplicate_of"]["name"] == "Pull-up"
    r = client.post("/exercises", json=body_from(analyze(client, "Pull ups")))
    assert r.status_code == 409 and "Pull-up" in r.json()["detail"]
    b = analyze(client, "Bulgarian split squats with pause")
    assert any("Bulgarian" in m["name"] for m in b["matches"])
    assert b["duplicate_of"] is None


def test_close_match_seeds_the_proposal_from_the_library(client, no_ai):
    a = analyze(client, "Barbell Bench Press (paused)")
    assert a["field_sources"]["muscles"] == "library"
    assert a["proposal"]["equipment"] == "barbell"


def test_model_reply_is_validated_field_by_field(client, monkeypatch):
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    reply = {
        "section": "gym",
        "equipment": "barbell",
        "measure": "reps",
        "pattern": "squat",
        "difficulty": "space-cadet",  # invalid: dropped, rules value stays
        "muscles": [
            {"region": "quads", "role": "primary"},
            {"region": "neck", "role": "primary"},  # unknown region: dropped
            {"region": "abs", "role": "secondary"},
        ],
        "instructions": ["Hold the bar in the crook of your elbows.", "Squat to depth."],
        "aliases": ["Zercher"],
    }
    monkeypatch.setattr(custom, "ask_model", lambda *a, **k: reply)
    a = analyze(client, "Zercher Squat")
    assert a["ai"]["status"] == "ok" and a["ai"]["model"] == "qwen3:4b"
    assert a["field_sources"]["muscles"] == "local_ai"
    assert {m["muscle"]: m["weight"] for m in a["proposal"]["muscles"]} == {
        "quads": 1.0,
        "abs": 0.5,
    }
    assert a["field_sources"]["difficulty"] != "local_ai"
    assert a["proposal"]["difficulty"] != "space-cadet"
    assert a["proposal"]["equipment"] == "barbell" and a["field_sources"]["equipment"] == "local_ai"
    assert a["proposal"]["instructions"][0].startswith("Hold the bar")


def test_model_failure_falls_back_to_rules(client, monkeypatch):
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def boom(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(custom, "ask_model", boom)
    a = analyze(client, "Zercher Squat")
    assert a["ai"]["status"] == "error"
    assert set(a["field_sources"].values()) <= {"rules", "library"}
    assert a["proposal"]["muscles"]


def test_no_model_installed_is_reported_not_fatal(client):
    a = analyze(client, "Zercher Squat")  # tests point Ollama at a closed port
    assert a["ai"]["status"] == "unavailable"
    assert a["proposal"]["pattern"] == "squat"


def test_create_log_stats_quests_and_outbox(client, profile, settings, no_ai):
    a = analyze(client, "Banded Pallof Hold")
    sources = dict(a["field_sources"], difficulty="user")
    r = client.post("/exercises", json=body_from(a, difficulty="beginner", field_sources=sources))
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["is_custom"] and e["source"] == "custom" and e["measure"] == "hold"
    assert e["field_sources"]["difficulty"] == "user" and e["difficulty"] == "beginner"
    assert e["slug"] == "custom-banded-pallof-hold"
    assert [x["id"] for x in client.get("/exercises", params={"custom": True}).json()] == [e["id"]]
    w = client.post("/workouts").json()["id"]
    assert (
        client.post(f"/workouts/{w}/sets", json={"exercise_id": e["id"], "reps": 8}).status_code
        == 422
    )
    logged = client.post(f"/workouts/{w}/sets", json={"exercise_id": e["id"], "duration_s": 30})
    assert logged.status_code == 201 and logged.json()["set"]["duration_s"] == 30
    oblique = next(m for m in client.get("/muscles").json() if m["key"] == "obliques")
    assert oblique["es_7d"] > 0
    con = sqlite3.connect(settings.db_url.removeprefix("sqlite:///"))
    row = con.execute("select payload from events_outbox where type = 'ExerciseAdded'").fetchone()
    assert row and json.loads(row[0])["exercise_id"] == e["id"]
    from app.modules.gamification.service import _exercise_refs

    db = client.app.state.session_factory()
    try:
        assert e["id"] in {ref.id for ref in _exercise_refs(db)}
    finally:
        db.close()


def test_validation_and_archive(client, no_ai):
    a = analyze(client, "Banded Pallof Hold")
    bad = body_from(a, muscles=[{"muscle": "neck", "weight": 1}])
    assert client.post("/exercises", json=bad).status_code == 422
    assert client.post("/exercises", json=body_from(a, met=5)).status_code == 422
    assert (
        client.post("/exercises", json=body_from(a, field_sources={"muscles": "magic"})).status_code
        == 422
    )
    e = client.post("/exercises", json=body_from(a)).json()
    w = client.post("/workouts").json()["id"]
    client.post(f"/workouts/{w}/sets", json={"exercise_id": e["id"], "duration_s": 20})
    assert client.delete(f"/exercises/{e['id']}").status_code == 204
    assert e["id"] not in [x["id"] for x in client.get("/exercises").json()]
    assert client.get(f"/workouts/{w}").json()["sets"][0]["exercise_name"] == "Banded Pallof Hold"
    pull = next(
        x
        for x in client.get("/exercises", params={"q": "Pull-up"}).json()
        if x["name"] == "Pull-up"
    )
    assert client.delete(f"/exercises/{pull['id']}").status_code == 409
