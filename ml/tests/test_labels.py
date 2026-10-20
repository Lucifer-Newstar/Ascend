from __future__ import annotations

import json

from check_labels import check, seed_foods
from common import ML_DIR


def test_repo_labels_resolve_to_food_rows() -> None:
    labels = json.loads((ML_DIR / "labels.json").read_text(encoding="utf-8"))
    assert check(labels, seed_foods()) == []


def test_reports_unknown_food_wrong_portion_and_missing_class() -> None:
    labels = {
        "classes": {
            "idli": {"food_name": "Idli", "default_portion": "1 katori", "en": "Idli", "ta": "x"},
            "pizza": {"food_name": "Pizza", "default_portion": "1 slice", "en": "Pizza", "ta": ""},
        }
    }
    errors = check(labels, {"Idli": "1 piece"}, classes=["idli", "pizza", "poha"])
    assert any("portion" in e for e in errors)
    assert any("Pizza" in e for e in errors)
    assert any("missing display name 'ta'" in e for e in errors)
    assert any(e.startswith("poha") for e in errors)
