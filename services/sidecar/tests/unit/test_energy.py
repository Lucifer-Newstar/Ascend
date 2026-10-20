import pytest

from app.modules.progress.energy import session_minutes, strength_kcal


def test_strength_kcal_met_formula():
    # 5.0 MET x 70 kg x 1 h = 350 kcal
    assert strength_kcal(60, 70) == pytest.approx(350)


def test_unfinished_session_uses_per_set_estimate():
    assert session_minutes(None, 8) == 20


def test_session_minutes_capped():
    assert session_minutes(500, 3) == 180
