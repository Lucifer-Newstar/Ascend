import pytest

from app.modules.progress.readiness import band_for, readiness


def test_best_and_worst_mornings():
    assert readiness(5, 5, "none", 5).score == 100
    assert readiness(1, 1, "a_lot", 1).score == 0


def test_weighted_formula_golden_values():
    # sleep 4 -> .75, energy 3 -> .5, some soreness -> .5, mood 4 -> .75
    # 100 x (.35x.75 + .30x.5 + .20x.5 + .15x.75) = 62.5 -> 62 (banker's rounding) -> amber
    r = readiness(4, 3, "some", 4)
    assert r.score == 62
    assert r.band == "amber"
    assert "one set shorter" in r.adjustment


def test_band_boundaries():
    assert band_for(70) == "green"
    assert band_for(69) == "amber"
    assert band_for(50) == "amber"
    assert band_for(49) == "red"


def test_bad_sleep_and_heavy_soreness_is_red():
    r = readiness(1, 2, "a_lot", 3)
    assert r.band == "red"
    assert "mobility" in r.adjustment


def test_scores_outside_1_to_5_raise():
    with pytest.raises(ValueError):
        readiness(0, 3, "none", 3)
