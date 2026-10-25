"""Food model gate: own photos only, every class covered, never a smoke build."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gate import decide

LABELS = {"classes": {"idli": {}, "dosa": {}, "not_food": {}}}
PARAMS = {
    "food_gate": {"min_own_per_class": 10, "min_own_top1": 0.7, "min_own_top3": 0.9},
    "export": {"version": "0.1.0"},
    "train": {"pretrained": True},
}


def metrics(
    top1: float = 0.8, top3: float = 0.95, per_class: tuple[int, ...] = (12, 11, 3)
) -> dict:
    classes = ["dosa", "idli", "not_food"]
    confusion = [[n if i == j else 0 for j in range(3)] for i, n in enumerate(per_class)]
    own = {"n": sum(per_class), "top1": top1, "top3": top3, "confusion": confusion}
    return {"classes": classes, "test_own": own}


def test_passes_with_enough_own_photos_and_accuracy() -> None:
    r = decide(metrics(), LABELS, PARAMS)
    assert r["passed"] and r["reasons"] == [] and r["own_photos"] == 26


def test_not_food_needs_no_own_photos_but_every_dish_does() -> None:
    r = decide(metrics(per_class=(12, 4, 0)), LABELS, PARAMS)
    assert not r["passed"]
    assert r["checks"]["own_photos_per_class"]["short"] == {"idli": 4}


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"top1": 0.6}, "top-1"),
        ({"top3": 0.8}, "top-3"),
    ],
)
def test_accuracy_floors(change: dict, reason: str) -> None:
    r = decide(metrics(**change), LABELS, PARAMS)
    assert not r["passed"] and any(reason in x for x in r["reasons"])


def test_smoke_builds_and_scratch_training_never_pass() -> None:
    smoke = {**PARAMS, "export": {"version": "0.0.0-smoke"}}
    assert "smoke build" in " ".join(decide(metrics(), LABELS, smoke)["reasons"])
    scratch = {**PARAMS, "train": {"pretrained": False}}
    assert not decide(metrics(), LABELS, scratch)["passed"]


def test_no_own_photos_fails() -> None:
    r = decide(metrics(per_class=(0, 0, 0)), LABELS, PARAMS)
    assert "no own photos in the test set" in r["reasons"]


def test_publish_refuses_a_failed_gate(tmp_path: Path) -> None:
    from publish_food import publish

    (tmp_path / "food-gate.json").write_text(json.dumps({"passed": False, "reasons": ["x"]}))
    with pytest.raises(SystemExit, match="gate did not pass"):
        publish(tmp_path, tmp_path / "release")
