"""The local model is preloaded on demand and warm calls use the normal timeout."""

from __future__ import annotations

from app.modules.coach import ollama, runtime


def test_warm_is_a_noop_without_ollama(client) -> None:
    r = client.post("/coach/warm").json()
    assert r == {"loaded": False, "model": "qwen3:4b", "seconds": 0.0}


def test_warm_then_short_timeout(client, profile, monkeypatch) -> None:
    runtime._warm.clear()
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)
    monkeypatch.setattr(ollama, "warm", lambda host, model, timeout=90.0: True)
    waits: list[float] = []

    def chat(*a, timeout=20.0, **k):
        waits.append(timeout)
        return "Rest well tonight."

    monkeypatch.setattr(ollama, "chat", chat)
    assert client.post("/coach/warm").json()["loaded"] is True
    client.get("/coach/tip")
    assert waits == [20.0]


def test_failures_are_counted_and_reset(client, profile, monkeypatch) -> None:
    runtime._warm.clear()
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def boom(*a, **k):
        raise ollama.OllamaTimeout("slow")

    monkeypatch.setattr(ollama, "chat", boom)
    client.get("/coach/tip")
    client.get("/coach/tip")
    with client.app.state.session_factory() as db:
        assert runtime.failures(db) == 2
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: "Rest well tonight.")
    client.get("/coach/tip")
    with client.app.state.session_factory() as db:
        assert runtime.failures(db) == 0


def test_the_model_picked_in_settings_is_used(client, profile, monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: True)

    def chat(host, model, *a, **k):
        seen.append(model)
        return "Rest well tonight."

    monkeypatch.setattr(ollama, "chat", chat)
    with client.app.state.session_factory() as db:
        from app.modules.progress import service as progress

        progress.set_setting(db, "coach_model", "qwen3:1.7b")
        db.commit()
    client.get("/coach/tip")
    assert seen == ["qwen3:1.7b"]
