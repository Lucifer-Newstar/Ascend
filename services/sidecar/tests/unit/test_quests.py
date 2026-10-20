from datetime import date, datetime, timedelta

from app.modules.gamification.quests import (
    ExerciseRef,
    difficulty_multiplier,
    generate_daily_quest,
)
from app.modules.progress.muscle_load import Contribution, compute_states

DAY = date(2026, 10, 20)
NOW = datetime(2026, 10, 20, 9, 0)
EXERCISES = [
    ExerciseRef(1, "Back Squat", {"quads": 1.0, "glutes": 1.0}),
    ExerciseRef(2, "Barbell Curl", {"biceps": 1.0}),
    ExerciseRef(3, "Bench Press", {"lower_chest": 1.0}),
]


def test_quest_has_training_nutrition_recovery():
    items = generate_daily_quest(DAY, compute_states([], NOW), EXERCISES, 120)
    assert [i.kind for i in items] == ["training", "nutrition", "recovery"]


def test_quest_is_deterministic_for_same_day():
    states = compute_states([], NOW)
    a = generate_daily_quest(DAY, states, EXERCISES, 120)
    b = generate_daily_quest(DAY, states, EXERCISES, 120)
    assert a == b


def test_training_item_avoids_recovering_muscles():
    contribs = [Contribution("quads", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    contribs += [Contribution("glutes", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    contribs += [Contribution("lower_chest", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    items = generate_daily_quest(DAY, compute_states(contribs, NOW), EXERCISES, 120)
    assert items[0].metric == "sets:biceps"


def test_missed_day_adds_gentle_comeback_item():
    items = generate_daily_quest(DAY, compute_states([], NOW), EXERCISES, 120, missed_yesterday=True)
    assert items[-1].code == "comeback"
    assert items[-1].xp <= 10


def test_difficulty_scaling():
    assert difficulty_multiplier(None) == 1.0
    assert difficulty_multiplier(0.4) == 0.9
    assert difficulty_multiplier(0.95) == 1.1
