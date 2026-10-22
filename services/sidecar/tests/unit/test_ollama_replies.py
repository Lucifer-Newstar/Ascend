"""Review L13: Ollama answering with JSON that is not an object must not become a 500."""

from __future__ import annotations

import httpx
import pytest

from app.modules.coach import ollama
from app.modules.workouts import custom

ODD_BODIES = [[], ["x"], "text", 3, {"message": "hi"}, {"message": {"content": 5}}, None]


def _reply(body):
    def fake(url, *a, **k):
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    return fake


@pytest.mark.parametrize("body", ODD_BODIES)
def test_chat_turns_odd_json_into_unavailable(monkeypatch, body) -> None:
    monkeypatch.setattr(ollama.httpx, "post", _reply(body))
    with pytest.raises(ollama.OllamaUnavailable):
        ollama.chat("http://127.0.0.1:11434", "m", "facts", "q")


@pytest.mark.parametrize("body", ODD_BODIES)
def test_ask_model_raises_value_error_not_attribute_error(monkeypatch, body) -> None:
    monkeypatch.setattr(custom.httpx, "post", _reply(body))
    with pytest.raises(ValueError):
        custom.ask_model("http://127.0.0.1:11434", "m", "Some move", "")


@pytest.mark.parametrize("body", [[], "x", {"models": "nope"}, {"models": [1, None]}])
def test_is_available_is_false_for_odd_tags(monkeypatch, body) -> None:
    monkeypatch.setattr(ollama.httpx, "get", _reply(body))
    assert ollama.is_available("http://127.0.0.1:11434", "m") is False
