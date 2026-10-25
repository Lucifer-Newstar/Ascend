"""Labelling functions, CLINC mapping, templates and the dataset leak rules."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import build_dataset
import clinc
import templates
import weak_label

INTENT_DIR = Path(__file__).resolve().parents[1] / "intent"


def test_weak_label_rules() -> None:
    assert weak_label.label("Knee pain after squats", ["squats"])[0] == "injury_pain"
    assert weak_label.label("How much protein per day?", ["nutrition"])[0] == "nutrition_question"
    assert weak_label.label("Proper form for the deadlift", ["deadlifts"])[0] == "exercise_howto"
    assert weak_label.label("How do I stay motivated?", [])[0] == "motivation"
    assert weak_label.label("Good beginner routine for home?", [])[0] == "plan_request"
    assert weak_label.label("Importance of rest days", ["recovery"])[0] == "training_question"
    # an injury TAG alone is not enough (warm-up questions carry it too)
    assert weak_label.label("Warming up before heavy lifts", ["injury"])[0] != "injury_pain"
    # "fast" (speed) is not food; "fasting" is
    assert weak_label.label("How fast should my base runs be?", ["running"])[0] != (
        "nutrition_question"
    )
    assert weak_label.label("Lifting while fasting", [])[0] == "nutrition_question"


def test_clinc_mapping() -> None:
    assert clinc.label("oos") == "out_of_scope"
    assert clinc.label("book_flight") == "out_of_scope"
    assert clinc.label("greeting") == "greeting"
    assert clinc.label("calories") == "nutrition_question"
    # things ASCEND does must never be taught as out-of-scope
    for kept_out in ("reminder", "change_user_name", "reset_settings", "recipe", "yes"):
        assert clinc.label(kept_out) is None


def test_templates_are_deterministic_and_split_by_template() -> None:
    a = templates.generate(per_template=3, seed=1)
    b = templates.generate(per_template=3, seed=1)
    assert a == b
    by_tpl: dict[str, set[str]] = {}
    for row in a:
        by_tpl.setdefault(row["template_id"], set()).add(row["split"])
    assert all(len(splits) == 1 for splits in by_tpl.values())
    labels = {r["label"] for r in a}
    assert {"log_set", "log_meal", "plan_edit", "undo_cancel", "greeting"} <= labels
    test_share = sum(r["split"] == "test" for r in a) / len(a)
    assert 0.1 < test_share < 0.45


def test_typo_changes_one_spot_only() -> None:
    import random

    rng = random.Random(0)
    for _ in range(50):
        t = templates.typo("pushups", rng)
        assert abs(len(t) - len("pushups")) <= 1
    assert templates.typo("ok", rng) == "ok"


def _fixture_raw(tmp: Path) -> Path:
    raw = tmp / "raw"
    raw.mkdir()
    hand_ids = [
        int(r["se_id"])
        for r in csv.DictReader((INTENT_DIR / "labels" / "se_handchecked.csv").open())
    ][:3]
    rows = [
        {
            "id": hand_ids[0],
            "title": "Knee pain when running",
            "tags": ["running"],
            "license": "CC BY-SA 3.0",
            "body_start": "",
            "score": 1,
        },
        {
            "id": hand_ids[1],
            "title": "Whey before bed?",
            "tags": ["protein"],
            "license": "CC BY-SA 3.0",
            "body_start": "",
            "score": 1,
        },
        {
            "id": 999001,
            "title": "Importance of Rest Days",
            "tags": ["recovery"],
            "license": "CC BY-SA 4.0",
            "body_start": "Why rest?",
            "score": 1,
        },
        {
            "id": 999002,
            "title": "Best grip for pull ups",
            "tags": ["pull-ups"],
            "license": "CC BY-SA 4.0",
            "body_start": "",
            "score": 1,
        },
        {
            "id": 999003,
            "title": "Is milk good after a workout",
            "tags": ["nutrition"],
            "license": "CC BY-SA 4.0",
            "body_start": "",
            "score": 1,
        },
    ]
    with (raw / "se_questions.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    data = {
        "train": [["what is my balance", "balance"], ["hello there", "greeting"]],
        "val": [["what's the weather", "weather"]],
        "test": [["book a flight to delhi", "book_flight"], ["set a reminder", "reminder"]],
        "oos_train": [["how tall is everest", "oos"]],
        "oos_val": [["who won the match", "oos"]],
        "oos_test": [["what is a stock split", "oos"]],
    }
    (raw / "clinc_data_full.json").write_text(json.dumps(data))
    return raw


PARAMS = {
    "seed": 3,
    "per_template": 2,
    "val_frac": 0.1,
    "clinc_per_intent": 5,
    "se_cap_per_label": 100,
}


def test_dataset_keeps_test_rows_out_of_training(tmp_path) -> None:
    raw = _fixture_raw(tmp_path)
    real = tmp_path / "real.json"
    real.write_text(json.dumps([["dataset:x", "Importance of rest days", "dataset"]]))
    stats = build_dataset.build(PARAMS, raw, tmp_path / "out", real_eval=real)
    out = tmp_path / "out"
    load = lambda n: [json.loads(x) for x in (out / f"{n}.jsonl").open()]  # noqa: E731
    train_val = load("train") + load("val")
    hand = {r["se_id"] for r in load("test_se_hand")}
    assert hand and not hand & {r.get("se_id") for r in train_val}
    # the real-question match (999001) is dropped from training
    assert 999001 not in {r.get("se_id") for r in train_val}
    # no text twice across splits
    names = ("train", "val", "test_templates", "test_clinc", "test_se_hand")
    seen: dict[str, str] = {}
    for n in names:
        for r in load(n):
            key = build_dataset.norm(r["text"])
            assert key not in seen or seen[key] == n
            seen[key] = n
    # CLINC: reminder dropped, flight is out of scope, oos kept
    clinc_test = {r["text"]: r["label"] for r in load("test_clinc")}
    assert clinc_test["book a flight to delhi"] == "out_of_scope"
    assert "set a reminder" not in clinc_test
    assert stats["splits"]["test_templates"]["rows"] > 0
