import csv
import io

from app.modules.coach import ollama


def log_workout(client):
    squat = next(e["id"] for e in client.get("/exercises", params={"q": "Back Squat"}).json())
    w = client.post("/workouts").json()
    for _ in range(3):
        client.post(
            f"/workouts/{w['id']}/sets",
            json={"exercise_id": squat, "weight_kg": 80, "reps": 5, "rpe": 8},
        )
    client.post(f"/workouts/{w['id']}/finish")


def test_coach_falls_back_to_rules_when_ollama_missing(client, profile):
    r = client.get("/coach/tip").json()
    assert r["source"] == "rules"
    assert r["fallback_reason"] == "ollama_unavailable"
    assert r["text"]


def test_coach_respects_ai_off(client, profile):
    client.put("/settings", json={"ai_enabled": False})
    r = client.post("/coach/ask", json={"question": "what should I train?"}).json()
    assert r["source"] == "rules" and r["fallback_reason"] == "ai_disabled"


def test_coach_uses_ollama_when_available(client, profile, monkeypatch):
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    seen = {}

    def fake_chat(host, model, facts, question, timeout=20.0, **kwargs):
        seen["facts"] = facts
        return "Train legs today."

    monkeypatch.setattr(ollama, "chat", fake_chat)
    r = client.post("/coach/ask", json={"question": "legs?"}).json()
    assert r == {
        "source": "ollama",
        "text": "Train legs today.",
        "tip_code": r["tip_code"],
        "model": "qwen3:4b",
        "fallback_reason": None,
        "checks": {"numbers": "pass", "banned": "pass", "version": "validate-1.0.0"},
    }
    assert "Rule-based tip" in seen["facts"]


def test_coach_falls_back_on_ollama_error(client, profile, monkeypatch):
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def boom(*a, **k):
        raise ollama.OllamaUnavailable("connection reset")

    monkeypatch.setattr(ollama, "chat", boom)
    r = client.get("/coach/tip").json()
    assert r["source"] == "rules" and r["fallback_reason"] == "model_error"


def test_a_timeout_is_named_and_counted(client, profile, monkeypatch):
    from app.modules.coach import runtime

    runtime._warm.clear()
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    waits: list[float] = []

    def slow(*a, timeout=20.0, **k):
        waits.append(timeout)
        raise ollama.OllamaTimeout("no reply")

    monkeypatch.setattr(ollama, "chat", slow)
    r = client.get("/coach/tip").json()
    assert r["source"] == "rules" and r["fallback_reason"] == "timeout"
    assert waits == [60.0]  # a cold model gets the long first-call timeout
    assert client.get("/settings").status_code == 200


def test_coach_status(client):
    assert client.get("/coach/status").json() == {
        "ai_enabled": True,
        "ollama_available": False,
        "model": "qwen3:4b",
    }


def test_history_groups_by_day(client, profile):
    log_workout(client)
    egg = next(f["id"] for f in client.get("/foods", params={"q": "Boiled egg"}).json())
    client.post(
        "/meals", json={"meal_type": "breakfast", "items": [{"food_id": egg, "portions": 2}]}
    )
    days = client.get("/history").json()
    assert len(days) == 1
    assert days[0]["sets"] == 3 and days[0]["kcal_in"] == 144
    assert days[0]["xp"] > 0


def test_export_json_and_csv(client, profile):
    log_workout(client)
    data = client.get("/export/json").json()
    assert data["export_schema_version"] == 2
    assert len(data["workouts"][0]["sets"]) == 3
    r = client.get("/export/csv/workouts")
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0][3] == "Exercise Name" and len(rows) == 4
    assert client.get("/export/csv/meals").text.startswith("Date,Meal,Food")
    assert client.get("/export/csv/bogus").status_code == 422
