"""Security review M4: OLLAMA_HOST in Ollama's own format works, and only loopback is
contacted unless the user opts in."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import load_settings, normalize_ollama_host
from app.modules.coach import ollama


@pytest.mark.parametrize(
    ("raw", "url"),
    [
        (None, "http://127.0.0.1:11434"),
        ("", "http://127.0.0.1:11434"),
        ("127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("127.0.0.1", "http://127.0.0.1:11434"),
        ("0.0.0.0", "http://127.0.0.1:11434"),
        ("0.0.0.0:12345", "http://127.0.0.1:12345"),
        ("localhost", "http://localhost:11434"),
        ("http://localhost:8080/", "http://localhost:8080"),
        ("http://127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("[::1]:11434", "http://[::1]:11434"),
        ("::", "http://[::1]:11434"),
        ("127.0.0.5", "http://127.0.0.5:11434"),
    ],
)
def test_ollama_style_values_become_urls(raw, url) -> None:
    assert normalize_ollama_host(raw) == url


@pytest.mark.parametrize(
    "raw",
    ["192.168.1.20", "http://gpu-box.lan:11434", "ollama.example.com", "10.0.0.2:11434"],
)
def test_non_loopback_hosts_are_refused_by_default(raw) -> None:
    assert normalize_ollama_host(raw) == ""


def test_remote_hosts_need_the_explicit_opt_in() -> None:
    assert normalize_ollama_host("192.168.1.20", allow_remote=True) == "http://192.168.1.20:11434"
    assert (
        normalize_ollama_host("https://gpu-box.lan", allow_remote=True) == "https://gpu-box.lan:443"
    )


@pytest.mark.parametrize(
    "raw", ["ftp://localhost", "http://", "http://user:pw@127.0.0.1", "localhost:notaport"]
)
def test_unusable_values_turn_the_coach_off(raw) -> None:
    assert normalize_ollama_host(raw) == ""


def test_settings_read_the_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "192.168.1.20")
    monkeypatch.delenv("ASCEND_OLLAMA_ALLOW_REMOTE", raising=False)
    assert load_settings().ollama_host == ""
    monkeypatch.setenv("ASCEND_OLLAMA_ALLOW_REMOTE", "1")
    assert load_settings().ollama_host == "http://192.168.1.20:11434"


def test_scheme_less_host_reaches_ollama(monkeypatch) -> None:
    """Before the fix f"{host}/api/tags" was "127.0.0.1:11434/api/tags": httpx raised
    UnsupportedProtocol, which was swallowed, so the coach always said Ollama is off."""
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    seen: list[str] = []

    def fake_get(url, timeout):
        seen.append(url)
        return httpx.Response(
            200, json={"models": [{"name": "qwen3:4b"}]}, request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(ollama.httpx, "get", fake_get)
    assert ollama.is_available(load_settings().ollama_host, "qwen3:4b") is True
    assert seen == ["http://127.0.0.1:11434/api/tags"]


def test_an_off_host_never_makes_a_request(monkeypatch) -> None:
    monkeypatch.setattr(ollama.httpx, "get", lambda *a, **k: pytest.fail("no request expected"))
    assert ollama.is_available("", "qwen3:4b") is False
    with pytest.raises(ollama.OllamaUnavailable):
        ollama.chat("", "qwen3:4b", "facts", "question")
