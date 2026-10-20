import pytest

from app.modules.workouts.pr import e1rm_or_none, epley_e1rm, is_new_pr


def test_epley_matches_plan_example():
    # Plan v2 worked example: 70 kg x 8 -> 88.7 kg
    assert round(epley_e1rm(70, 8), 1) == 88.7


def test_single_rep_is_the_weight():
    assert epley_e1rm(100, 1) == 100


def test_high_rep_sets_are_not_used_for_prs():
    assert e1rm_or_none(40, 15) is None


def test_bodyweight_sets_are_not_used_for_prs():
    assert e1rm_or_none(0, 8) is None


def test_first_set_is_baseline_not_pr():
    assert is_new_pr(88.7, None) is False


def test_strictly_higher_is_pr():
    assert is_new_pr(90.0, 88.7) is True
    assert is_new_pr(88.7, 88.7) is False


def test_negative_weight_rejected():
    with pytest.raises(ValueError):
        epley_e1rm(-1, 5)
