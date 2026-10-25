"""edit_parser (v1.3 wave 2): which chat lines are edits, and which are not."""

from __future__ import annotations

import pytest

from app.modules.actions.edit_parser import parse_edit, weekday


@pytest.mark.parametrize(
    ("text", "kind", "params"),
    [
        ("change my goal to bulk", "update_profile", {"field": "goal", "value": "bulk"}),
        ("my goal is to lose fat", "update_profile", {"field": "goal", "value": "cut"}),
        ("set my age to 22", "update_profile", {"field": "age", "value": 22}),
        ("I'm 21 years old", "update_profile", {"field": "age", "value": 21}),
        ("my height is 5'7", "update_profile", {"field": "height_cm", "value": 170.2}),
        ("i am 170 cm tall", "update_profile", {"field": "height_cm", "value": 170.0}),
        ("I want to reach 50 kg", "update_profile", {"field": "target_weight_kg", "value": 50.0}),
        ("call me Navin", "update_profile", {"field": "name", "value": "Navin"}),
        ("i'm a beginner", "update_profile", {"field": "experience", "value": "beginner"}),
        ("switch to lbs", "update_setting", {"key": "units", "value": "imperial"}),
        ("use kg", "update_setting", {"key": "units", "value": "metric"}),
        ("dark mode", "update_setting", {"key": "theme", "value": "dark"}),
        ("turn off reminders", "update_setting", {"key": "reminders", "value": False}),
        ("disable ai", "update_setting", {"key": "ai_enabled", "value": False}),
        ("hide calories", "update_setting", {"key": "hide_calories", "value": True}),
        ("switch trainer to vera", "update_setting", {"key": "trainer_id", "value": "vera"}),
        ("I have a bench", "set_equipment", {"add": ["bench"], "remove": []}),
        ("I got a pull-up bar", "set_equipment", {"add": ["pullup_bar"], "remove": []}),
        ("I have an 8kg dumbbell and two 5kg dumbbells", "set_equipment", {"add": ["dumbbells"]}),
        ("I don't have rings anymore", "set_equipment", {"add": [], "remove": ["rings"]}),
        ("i joined a gym", "set_equipment", {"add": ["gym"]}),
        ("swap bench press for push-ups", "edit_plan",
         {"op": "swap", "exercise": "bench press", "new_exercise": "push-ups"}),
        ("remove lateral raise from my plan", "edit_plan",
         {"op": "remove", "exercise": "lateral raise"}),
        ("add 2 sets of plank to my plan on friday", "edit_plan",
         {"op": "add", "exercise": "plank", "sets": 2, "weekday": 4}),
        ("make squats 4 sets", "edit_plan", {"op": "sets", "exercise": "squats", "sets": 4}),
        ("change push-ups to 8-12 reps", "edit_plan", {"op": "reps", "rep_low": 8, "rep_high": 12}),
        ("move leg day to saturday", "edit_plan",
         {"op": "move_day", "day": "leg", "to_weekday": 5}),
        ("rest 90s on squats", "edit_plan", {"op": "rest", "exercise": "squats", "rest_s": 90}),
        ("set rest for bench press to 2 min", "edit_plan",
         {"op": "rest", "exercise": "bench press", "rest_s": 120}),
        ("make squats rest 45 seconds", "edit_plan", {"op": "rest", "rest_s": 45}),
        ("train 4 days a week", "update_setting", {"key": "sessions_per_week", "value": 4}),
        ("i can train five days a week", "update_setting", {"value": 5}),
        ("set days per week to 3", "update_setting", {"key": "sessions_per_week", "value": 3}),
        ("move monday to tue", "edit_plan", {"op": "move_day", "weekday": 0, "to_weekday": 1}),
    ],
)  # fmt: skip
def test_edit_lines(text: str, kind: str, params: dict[str, object]) -> None:
    hit = parse_edit(text)
    assert hit is not None and hit[0] == kind, (text, hit)
    for k, v in params.items():
        assert hit[1][k] == v, (text, k, hit)


@pytest.mark.parametrize(
    "text",
    [
        "what is my goal?",
        "how do i change my theme",
        "should I switch to lbs?",
        "10 pushups",
        "i have 2 idli",
        "add food ragi dosa 120 kcal",
        "switch to ppl",
        "I have a punching bag",
        "delete everything",
        "rest day",
        "switch me to upper lower",
        "change my plan to ppl",
        "how long should i rest between squats?",
    ],
)
def test_not_edits(text: str) -> None:
    assert parse_edit(text) is None


def test_weekday_names() -> None:
    assert [weekday(w) for w in ("monday", "Tue", "weds", "thursday", "sat", "sundays")] == [
        0, 1, 2, 3, 5, 6,
    ]  # fmt: skip
