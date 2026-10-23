"""ai-tiers-v1: the model recommendation follows VRAM first, then RAM."""

from __future__ import annotations

import pytest

from app.modules.ai.setup import recommend, smaller_than


@pytest.mark.parametrize(
    ("ram", "vram", "model"),
    [
        (16.0, 6.0, "qwen3:4b"),
        (16.0, 4.0, "qwen3:4b"),
        (8.0, 3.0, "qwen3:1.7b"),
        (32.0, None, "qwen3:1.7b"),
        (8.0, None, "qwen3:0.6b"),
        (None, None, "qwen3:0.6b"),
        (4.0, None, None),
        (6.0, 1.0, None),
    ],
)
def test_recommend(ram: float | None, vram: float | None, model: str | None) -> None:
    r = recommend(ram, vram)
    assert r.model == model and r.reason


def test_smaller_model_chain() -> None:
    assert smaller_than("qwen3:4b") == "qwen3:1.7b"
    assert smaller_than("qwen3:1.7b") == "qwen3:0.6b"
    assert smaller_than("qwen3:0.6b") is None
    assert smaller_than("llama3.2:3b") == "qwen3:0.6b"
