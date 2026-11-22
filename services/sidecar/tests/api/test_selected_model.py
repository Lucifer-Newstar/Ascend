"""The AI setup model selection must apply to every optional wording path."""

import pytest

from app.modules.coach import ollama
from app.modules.intelligence import explain
from app.modules.workouts import custom


@pytest.fixture(autouse=True)
def selected_model(client, profile, monkeypatch):
    explain.clear_cache()
    monkeypatch.setattr(
        ollama,
        "server_info",
        lambda host, timeout=1.5: (
            "test",
            [("qwen3:0.6b", 500_000_000), ("qwen3:1.7b", 1_400_000_000)],
        ),
    )
    monkeypatch.setattr(ollama, "is_available", lambda *args, **kwargs: True)
    assert client.put("/ai/model", json={"model": "qwen3:0.6b"}).status_code == 200
    client.put("/settings", json={"ai_enabled": True})
    yield
    explain.clear_cache()


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/planner/diet", {"diet": "veg", "use_ai": True}),
        ("/planner/workout", {"days_per_week": 3, "use_ai": True}),
    ],
)
def test_planners_use_selected_model(client, monkeypatch, path, body):
    calls = []

    def chat(host, model, facts, question, **kwargs):
        calls.append(model)
        return facts

    monkeypatch.setattr(ollama, "chat", chat)
    r = client.post(path, json=body)
    assert r.status_code == 200, r.text
    assert calls == ["qwen3:0.6b"]
    assert r.json()["phrased_by"] == "ollama"


def test_explanations_follow_model_switch_including_cached_value(client, monkeypatch):
    calls = []

    def chat(host, model, facts, question, **kwargs):
        calls.append(model)
        return question.removeprefix("Rewrite the explanation for the lifter: ")

    monkeypatch.setattr(ollama, "chat", chat)
    for chosen in ("qwen3:0.6b", "qwen3:1.7b", None):
        client.put("/ai/model", json={"model": chosen})
        e = client.get("/intelligence/tdee/explanation").json()
        expected = chosen or client.app.state.settings.coach_model
        assert e["phrasing"] == "model"
        assert e["model"] == expected
        assert calls[-1] == expected
    assert len(calls) == 3


def test_custom_exercise_analysis_uses_selected_model(client, monkeypatch):
    calls = []
    original = custom.analyse

    def analyse(*args, **kwargs):
        calls.append(kwargs["model"])
        # Keep network/model calls out of this routing regression.
        kwargs["ai_enabled"] = False
        return original(*args, **kwargs)

    monkeypatch.setattr(custom, "analyse", analyse)
    r = client.post("/exercises/analyze", json={"name": "QA press", "online": False})
    assert r.status_code == 200, r.text
    assert calls == ["qwen3:0.6b"]
