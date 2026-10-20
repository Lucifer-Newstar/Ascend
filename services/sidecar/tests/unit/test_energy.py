import pytest

from app.modules.progress.energy import session_minutes, strength_kcal


def test_strength_kcal_met_formula():
    # 5.0 MET x 70 kg x 1 h = 350 kcal
    assert strength_kcal(60, 70) == pytest.approx(350)


def test_unfinished_session_uses_per_set_estimate():
    assert session_minutes(None, 8) == 20


def test_session_minutes_capped():
    assert session_minutes(500, 3) == 180


def test_workout_kcal_mixes_timed_mets_and_lifting_minutes():
    from app.modules.progress.energy import workout_kcal

    # 30-min run at MET 9.8 for 70 kg = 343 kcal; no lifting sets.
    assert round(workout_kcal(35, 0, [(9.8, 1800)], 70)) == 343
    # 60-min session: 20 min of rope (11.8) + 40 min of lifting (MET 5).
    rope = 11.8 * 70 * (20 / 60)
    lifting = 5.0 * 70 * (40 / 60)
    assert round(workout_kcal(60, 6, [(11.8, 1200)], 70)) == round(rope + lifting)
    # Unfinished session with lifting only: 2.5 min per set.
    assert round(workout_kcal(None, 4, [], 70)) == round(5.0 * 70 * (10 / 60))
