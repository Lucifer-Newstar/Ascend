"""Hunter stats (stats-v1): each score from its documented formula."""

from app.modules.gamification.stats import StatInputs, compute_stats


def by_key(inputs: StatInputs) -> dict[str, int]:
    return {s.key: s.value for s in compute_stats(inputs)}


def test_a_new_user_scores_zero_everywhere():
    assert by_key(StatInputs()) == {"str": 0, "agi": 0, "end": 0, "vit": 0, "int": 0}


def test_strength_takes_the_better_route():
    # Skill trees: 6 of 20 steps = 30. Lifting: 105 kg e1RM at 70 kg = 1.5x -> 75.
    lifter = StatInputs(strength_steps=(6, 20), best_e1rm_kg=105, bodyweight_kg=70)
    assert by_key(lifter)["str"] == 75
    # Without a weighted lift, the skill-tree share counts on its own.
    assert by_key(StatInputs(strength_steps=(6, 20)))["str"] == 30
    # Capped at 100 above 2.0x body weight.
    assert by_key(StatInputs(best_e1rm_kg=200, bodyweight_kg=70))["str"] == 100


def test_endurance_is_cardio_minutes_against_600():
    assert by_key(StatInputs(cardio_min=150))["end"] == 25
    assert by_key(StatInputs(cardio_min=900))["end"] == 100


def test_vitality_and_discipline_are_half_and_half():
    i = StatInputs(checkin_days=14, mean_readiness=70, meal_days=21, quest_done=30, quest_total=60)
    s = by_key(i)
    assert s["vit"] == 60  # 0.5 * 14/28 + 0.5 * 0.70
    assert s["int"] == 62  # 0.5 * 21/28 + 0.5 * 30/60 = 0.625 -> 62 (banker's rounding)


def test_every_stat_carries_its_formula_and_inputs():
    for s in compute_stats(StatInputs(skill_steps=(3, 40))):
        assert s.formula and s.inputs
        assert 0 <= s.value <= 100
