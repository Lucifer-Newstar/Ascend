"""AI setup: detection, model choice, the failure suggestion and the test call."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.ai import hardware
from app.modules.coach import ollama, runtime


def fake_ollama(monkeypatch, models: list[tuple[str, int]]) -> None:
    monkeypatch.setattr(ollama, "server_info", lambda host, timeout=1.5: ("0.12.6", models))
    names = {n for n, _ in models}
    monkeypatch.setattr(ollama, "is_available", lambda host, model, timeout=1.5: model in names)
    monkeypatch.setattr(hardware, "detect", lambda: hardware.Hardware(16.0, 4.0, "RTX 3050"))


def test_without_ollama_the_tier_is_rules(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(hardware, "detect", lambda: hardware.Hardware(8.0, None, None))
    monkeypatch.setattr(hardware, "ollama_installed", lambda: False)
    s = client.get("/ai/setup").json()
    assert s["tier"] == "rules" and not s["ollama_running"] and not s["ollama_installed"]
    assert s["recommended"]["model"] == "qwen3:0.6b"
    assert s["recommended"]["pull_command"] == "ollama pull qwen3:0.6b"
    assert "vision" not in s  # v1.3: photo feedback and its vision model are removed


def test_detects_models_and_switches(client: TestClient, monkeypatch) -> None:
    fake_ollama(monkeypatch, [("qwen3:4b", 2_500_000_000), ("qwen3:1.7b", 1_400_000_000)])
    s = client.get("/ai/setup").json()
    assert s["tier"] == "ai" and s["model"] == "qwen3:4b" and s["ollama_version"] == "0.12.6"
    assert s["models"] == [
        {"name": "qwen3:4b", "size_gb": 2.5},
        {"name": "qwen3:1.7b", "size_gb": 1.4},
    ]
    assert s["hardware"] == {"ram_gb": 16.0, "vram_gb": 4.0, "gpu": "RTX 3050"}
    s = client.put("/ai/model", json={"model": "qwen3:1.7b"}).json()
    assert s["model"] == "qwen3:1.7b"
    r = client.put("/ai/model", json={"model": "llama3.2:3b"})
    assert r.status_code == 422 and "ollama pull llama3.2:3b" in r.text
    assert client.put("/ai/model", json={"model": "bad model;rm"}).status_code == 422
    assert client.put("/ai/model", json={"model": None}).json()["model"] == "qwen3:4b"


def test_repeated_timeouts_suggest_a_smaller_model(client: TestClient, profile, monkeypatch):
    fake_ollama(monkeypatch, [("qwen3:4b", 2_500_000_000)])
    runtime._warm.clear()

    def slow(*a, **k):
        raise ollama.OllamaTimeout("slow")

    monkeypatch.setattr(ollama, "chat", slow)
    for _ in range(3):
        client.get("/coach/tip")
    s = client.get("/ai/setup").json()
    assert s["failures"] == 3 and "qwen3:1.7b" in s["suggestion"]
    t = client.post("/ai/test").json()
    assert t["ok"] is False and t["reason"] == "timeout"
    monkeypatch.setattr(ollama, "chat", lambda *a, **k: "Ready when you are.")
    t = client.post("/ai/test").json()
    assert t["ok"] is True and t["reply"] == "Ready when you are."
    assert client.get("/ai/setup").json()["suggestion"] is None
