"""actions-parse-v2 (v1.3): the everyday log lines the trainer test found failing."""

from __future__ import annotations

import pytest

from app.modules.actions.parser import meal_type_for, parse


@pytest.mark.parametrize(
    ("text", "kind", "expect"),
    [
        ("pushups 3x10", "log_set", {"sets": 3, "reps": 10, "weight_kg": 0}),
        ("squats 3x12", "log_set", {"sets": 3, "reps": 12}),
        ("bench 80x5", "log_set", {"sets": 1, "reps": 5, "weight_kg": 80}),
        ("3 sets 10 reps pushups", "log_set", {"sets": 3, "reps": 10}),
        ("3 set 10 rep pushup", "log_set", {"sets": 3, "reps": 10}),
        ("bench 20kg 8 reps", "log_set", {"reps": 8, "weight_kg": 20}),
        ("bench press 20kg for 8 reps", "log_set", {"reps": 8, "weight_kg": 20}),
        ("8 reps bench 20kg", "log_set", {"reps": 8, "weight_kg": 20}),
        ("10kg db curl 10 reps", "log_set", {"reps": 10, "weight_kg": 10}),
        ("pullups 7", "log_count", {"name": "pullups", "count": 7}),
        ("dips 12", "log_count", {"name": "dips", "count": 12}),
        ("10 pushups done", "log_count", {"name": "pushups", "count": 10}),
        ("10 pushups today", "log_count", {"name": "pushups", "count": 10}),
        ("just did 10 pushups \U0001f4aa", "log_count", {"name": "pushups", "count": 10}),
        ("machan 10 pushups pannen", "log_count", {"name": "pushups", "count": 10}),
        ("bro did 10 pushups da", "log_count", {"name": "pushups", "count": 10}),
        ("aaj 10 pushups kiye", "log_count", {"name": "pushups", "count": 10}),
        ("twenty pushups", "log_count", {"count": 20}),
        ("15 pushup s", "log_count", {"name": "pushups", "count": 15}),
        ("plank 1 min", "log_hold", {"seconds": 60}),
        ("1 min plank", "log_hold", {"seconds": 60}),
        ("plank for a minute", "log_hold", {"seconds": 60}),
        ("plank 1:30", "log_hold", {"seconds": 90}),
        ("plank 1 min 30 sec", "log_hold", {"seconds": 90}),
        ("plank 1.5 min", "log_hold", {"seconds": 90}),
        ("held plank for 60 seconds", "log_hold", {"seconds": 60}),
        ("60 sec dead hang", "log_hold", {"exercise": "dead hang", "seconds": 60}),
        ("3x30s plank", "log_hold", {"seconds": 30, "sets": 3}),
        ("plank 3 x 30 sec", "log_hold", {"seconds": 30, "sets": 3}),
        ("my weight is 42 kg", "log_weight", {"weight_kg": 42}),
        ("i'm 42 kg", "log_weight", {"weight_kg": 42}),
        ("I'm 42.5 kg today", "log_weight", {"weight_kg": 42.5}),
        ("weighed 42kg today", "log_weight", {"weight_kg": 42}),
        ("42kg", "log_weight", {"weight_kg": 42}),
        ("weight: 42.5kg", "log_weight", {"weight_kg": 42.5}),
        ("curd rice for lunch", "log_meal", {"food": "curd rice", "meal_type": "lunch"}),
        ("1 katori dal rice", "log_meal", {"food": "dal rice", "portions": 1}),
        ("ate half katori dal", "log_meal", {"food": "dal", "portions": 0.5}),
        ("half plate biryani", "log_meal", {"food": "biryani", "portions": 0.5}),
        ("1.5 cup curd rice", "log_meal", {"food": "curd rice", "portions": 1.5}),
        ("ate 200 grams chicken", "log_food_grams", {"food": "chicken", "grams": 200}),
        ("milk 250ml", "log_food_grams", {"food": "milk", "grams": 250}),
    ],
)
def test_everyday_lines(text: str, kind: str, expect: dict[str, object]) -> None:
    got = parse(text, "metric", 13)
    assert got is not None and got.kind == kind, (text, got)
    for key, want in expect.items():
        assert got.params[key] == want, (text, key, got.params)


@pytest.mark.parametrize(
    ("text", "names", "meal"),
    [
        ("2 idli and sambar for breakfast", ["idli", "sambar"], "breakfast"),
        ("ven pongal, coconut chutney", ["ven pongal", "coconut chutney"], None),
        ("1 ven pongal and 1 coconut chutney for breakfast", ["ven pongal", "coconut chutney"],
         "breakfast"),
        ("breakfast: 2 idli + coconut chutney", ["idli", "coconut chutney"], "breakfast"),
        ("had rice, sambar, poriyal for lunch", ["rice", "sambar", "poriyal"], "lunch"),
        ("dosa with chutney", ["dosa", "chutney"], None),
        ("10 pushups and 10 squats", ["pushups", "squats"], None),
    ],
)  # fmt: skip
def test_several_items_in_one_line(text: str, names: list[str], meal: str | None) -> None:
    got = parse(text, "metric", 13)
    assert got is not None and got.kind == "log_items", (text, got)
    assert [i["name"] for i in got.params["items"]] == names
    if meal:
        assert got.params["meal_type"] == meal


@pytest.mark.parametrize(
    "text",
    [
        "what should i eat for dinner",
        "Running with a backpack",
        "Small woman and want to get bigger",
        "Can creatine and citrus be combined?",
        "what is my bmi",
        "set my age to 21",
        "ok",
        "what's my workout today",
    ],
)
def test_sentences_are_not_log_lines(text: str) -> None:
    got = parse(text, "metric", 13)
    # A sentence may come back as loose items; the service then drops anything that is not
    # a known dish, so it never becomes a card (tests/api/test_v13_trainer.py).
    assert got is None or (
        got.kind == "log_items" and all(i.get("bare") for i in got.params["items"])
    )


def test_meal_type_by_the_clock_has_a_snack_afternoon() -> None:
    assert [meal_type_for(None, h) for h in (8, 13, 16, 20, 23)] == [
        "breakfast",
        "lunch",
        "snack",
        "dinner",
        "snack",
    ]
