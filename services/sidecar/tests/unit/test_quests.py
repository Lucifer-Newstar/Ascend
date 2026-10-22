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
    ExerciseRef(1, "Back Squat", {"vastus_lateralis": 1.0, "gluteus_maximus": 1.0}),
    ExerciseRef(2, "Barbell Curl", {"biceps_long": 1.0}),
    ExerciseRef(3, "Bench Press", {"pec_major_sternal": 1.0}),
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
    contribs = [Contribution("vastus_lateralis", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    contribs += [Contribution("gluteus_maximus", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    contribs += [Contribution("pec_major_sternal", 1.0, NOW - timedelta(hours=6)) for _ in range(9)]
    contribs += [Contribution("biceps_long", 1.0, NOW - timedelta(days=5))]  # trained, under
    states = compute_states(contribs, NOW)
    items = generate_daily_quest(DAY, states, EXERCISES, 120)
    assert items[0].metric == "sets:biceps_long"
    recovering = {"sets:vastus_lateralis", "sets:gluteus_maximus", "sets:pec_major_sternal"}
    assert generate_daily_quest(DAY, states, EXERCISES, 120)[0].metric not in recovering


def test_readiness_only_muscles_are_never_quest_targets():
    rotator = [ExerciseRef(9, "External Rotation", {"infraspinatus": 1.0, "teres_minor": 1.0})]
    items = generate_daily_quest(DAY, compute_states([], NOW), rotator, 120)
    assert items[0].metric == "manual"


def test_missed_day_adds_gentle_comeback_item():
    items = generate_daily_quest(
        DAY, compute_states([], NOW), EXERCISES, 120, missed_yesterday=True
    )
    assert items[-1].code == "comeback"
    assert items[-1].xp <= 10


def test_difficulty_scaling():
    assert difficulty_multiplier(None) == 1.0
    assert difficulty_multiplier(0.4) == 0.9
    assert difficulty_multiplier(0.95) == 1.1


def test_apply_readiness_resizes_only_training_items():
    from app.modules.gamification.quests import QuestItemSpec, apply_readiness

    item = QuestItemSpec(
        "training",
        "train_vastus_lateralis",
        "3 hard sets for quads",
        "Suggested: Back Squat.",
        "sets:vastus_lateralis",
        3,
        40,
    )
    assert apply_readiness(item, None) == item
    assert apply_readiness(item, "green") == item
    amber = apply_readiness(item, "amber")
    assert (amber.target, amber.title) == (2, "2 hard sets for quads")
    red = apply_readiness(item, "red")
    assert red.code == "mobility_15" and red.metric == "manual"
    meal = QuestItemSpec("nutrition", "log_meals", "Log 3 meals", "", "meals", 3, 25)
    assert apply_readiness(meal, "red") == meal
