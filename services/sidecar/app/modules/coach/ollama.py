"""Minimal client for a local Ollama server (http://127.0.0.1:11434 by default).

Only localhost is ever contacted. Every call has a short timeout; on any error
the caller falls back to the rule-based tip, so the app works without AI.
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


def is_available(host: str, model: str, timeout: float = 1.5) -> bool:
    try:
        r = httpx.get(f"{host}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = {m.get("name", "") for m in r.json().get("models", [])}
        return model in names or f"{model}:latest" in names
    except (httpx.HTTPError, ValueError):
        return False


def chat(host: str, model: str, facts: str, question: str, timeout: float = 20.0) -> str:
    payload = {
        "model": model,
        "stream": False,
        "think": False,  # qwen3: skip the hidden reasoning pass for faster replies
        "options": {"temperature": 0.4, "num_predict": 220},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Facts (from the app's own formulas):\n{facts}\n\nQuestion: {question}"},
        ],
    }
    try:
        r = httpx.post(f"{host}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        content = r.json().get("message", {}).get("content", "")
    except (httpx.HTTPError, ValueError) as e:
        raise OllamaUnavailable(str(e)) from e
    text = THINK_RE.sub("", content).strip()
    if not text:
        raise OllamaUnavailable("empty reply")
    return text
