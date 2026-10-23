"""Minimal client for a local Ollama server (http://127.0.0.1:11434 by default).

Only localhost is contacted unless the user opts in to a remote Ollama (the host
comes from config.normalize_ollama_host; "" means off). Every call has a short
timeout; on any error the caller falls back to the rule-based tip, so the app
works without AI.
"""

from __future__ import annotations

import re

import httpx

SYSTEM_PROMPT = (
    "You are ARC, the coach inside the ASCEND fitness app. Be brief (max 3 sentences), "
    "warm and specific. Use ONLY the numbers in the provided facts; never invent numbers. "
    "Do not give medical diagnoses; suggest seeing a professional for pain or injury."
)
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class OllamaUnavailable(Exception):
    pass


class OllamaTimeout(OllamaUnavailable):
    """The model did not answer in time (often the first, cold load of the model)."""


# How long Ollama keeps the model in memory after a request (its own `keep_alive`), so the
# next question doesn't pay the cold load again.
KEEP_ALIVE = "30m"


def reply_content(body: object) -> str:
    """message.content of an /api/chat reply. Raises ValueError for any other shape (a
    list, a string, a message that isn't an object), so callers never see AttributeError."""
    message = body.get("message") if isinstance(body, dict) else None
    content = message.get("content", "") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ValueError("unexpected reply from Ollama")
    return content


def is_available(host: str, model: str, timeout: float = 1.5) -> bool:
    if not host:
        return False
    try:
        r = httpx.get(f"{host}/api/tags", timeout=timeout)
        r.raise_for_status()
        body = r.json()
        models = body.get("models", []) if isinstance(body, dict) else []
        if not isinstance(models, list):
            return False
        names = {m.get("name", "") for m in models if isinstance(m, dict)}
        return model in names or f"{model}:latest" in names
    except (httpx.HTTPError, ValueError):
        return False


def chat(
    host: str,
    model: str,
    facts: str,
    question: str,
    timeout: float = 20.0,
    system: str = SYSTEM_PROMPT,
    format: dict[str, object] | None = None,
) -> str:
    if not host:
        raise OllamaUnavailable("no usable OLLAMA_HOST")
    payload = {
        "model": model,
        "stream": False,
        "think": False,  # qwen3: skip the hidden reasoning pass for faster replies
        "keep_alive": KEEP_ALIVE,
        **({"format": format} if format else {}),
        "options": {"temperature": 0.4, "num_predict": 220},
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Facts (from the app's own formulas):\n{facts}\n\nQuestion: {question}",
            },
        ],
    }
    try:
        r = httpx.post(f"{host}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        content = reply_content(r.json())
    except httpx.TimeoutException as e:
        raise OllamaTimeout(f"no reply in {timeout:g} s") from e
    except (httpx.HTTPError, ValueError) as e:
        raise OllamaUnavailable(str(e)) from e
    text = THINK_RE.sub("", content).strip()
    if not text:
        raise OllamaUnavailable("empty reply")
    return text


def warm(host: str, model: str, timeout: float = 90.0) -> bool:
    """Load the model into memory without generating anything (an empty generate request,
    Ollama's documented way to preload), so the first real question is fast."""
    if not host:
        return False
    try:
        r = httpx.post(
            f"{host}/api/generate",
            json={"model": model, "keep_alive": KEEP_ALIVE},
            timeout=timeout,
        )
        r.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def server_info(host: str, timeout: float = 1.5) -> tuple[str | None, list[tuple[str, int]]]:
    """(Ollama's version, installed models as (name, bytes)), or (None, []) when it isn't
    running. Both are Ollama's own local endpoints (/api/version, /api/tags)."""
    if not host:
        return None, []
    try:
        v = httpx.get(f"{host}/api/version", timeout=timeout)
        v.raise_for_status()
        t = httpx.get(f"{host}/api/tags", timeout=timeout)
        t.raise_for_status()
        version = v.json().get("version")
        models = t.json().get("models", [])
    except (httpx.HTTPError, ValueError, AttributeError):
        return None, []
    out = [
        (str(m.get("name", "")), int(m.get("size", 0) or 0))
        for m in models
        if isinstance(m, dict) and m.get("name")
    ]
    return (str(version) if version else "unknown"), out
