"""actions-parse-v1 agrees with the command bar on the shared vectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.actions.parser import parse

VECTORS = json.loads(
    (Path(__file__).parents[4] / "packages/shared/src/command-vectors.json").read_text("utf-8")
)["vectors"]


@pytest.mark.parametrize("v", VECTORS, ids=[v["text"] for v in VECTORS])
def test_shared_vectors(v: dict) -> None:
    got = parse(v["text"], "metric", 13)
    if v["kind"] is None:
        assert got is None
        return
    assert got is not None and got.kind == v["kind"]
    for k, want in v["params"].items():
        assert (
            got.params[k] == pytest.approx(want)
            if isinstance(want, float)
            else got.params[k] == want
        )


@pytest.mark.parametrize(
    ("text", "kind", "key", "value"),
    [
        ("i weigh 72.5 kg", "log_weight", "weight_kg", 72.5),
        ("i ate 2 idli for breakfast", "log_meal", "meal_type", "breakfast"),
        ("switch me to PPL", "follow_program", "program", "ppl"),
        ("I did 3 sets of 10 push-ups", "log_set", "sets", 3),
        ("bench 135 x 5", "log_set", "weight_kg", 135),
    ],
)
def test_more_phrasings(text: str, kind: str, key: str, value: object) -> None:
    got = parse(text)
    assert got is not None and got.kind == kind and got.params[key] == value


def test_imperial_units_convert() -> None:
    got = parse("bench 135 x 5", "imperial")
    assert got is not None and got.params["weight_kg"] == pytest.approx(61.23, abs=0.01)
    assert parse("hello") is None
