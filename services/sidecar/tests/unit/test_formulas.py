import pytest

from app.modules.gamification import formulas as f


def test_level_curve_matches_plan_values():
    assert f.xp_to_next(1) == 100
    assert f.xp_to_next(10) == 1995
    assert f.xp_to_next(14) == 3090


def test_level_from_total_xp():
    info = f.level_from_total(0)
    assert (info.level, info.xp_into_level) == (1, 0)
    info = f.level_from_total(100)
    assert (info.level, info.xp_into_level) == (2, 0)
    info = f.level_from_total(100 + 246 + 10)
    assert info.level == 3 and info.xp_into_level == 10


def test_level_progress_fraction():
    assert f.level_from_total(50).progress == pytest.approx(0.5)


@pytest.mark.parametrize(
    "level,letter",
    [(1, "E"), (9, "E"), (10, "D"), (20, "C"), (35, "B"), (50, "A"), (69, "A"), (70, "S")],
)
def test_rank_thresholds(level, letter):
    assert f.rank_for_level(level)[0] == letter


def test_set_xp_hard_vs_easy():
    assert f.set_xp(8) == 3
    assert f.set_xp(6) == 1
    assert f.set_xp(None) == 3  # no RPE logged -> counts as working set


def test_session_xp_respects_cap():
    assert f.session_completion_xp(40, 0) == 40  # 20 + 0.5*40
    assert f.session_completion_xp(400, 100) == 50  # capped at 150 total


def test_meal_xp_daily_cap():
    assert [f.meal_xp(n) for n in range(6)] == [5, 5, 5, 5, 0, 0]


def test_streak_multiplier_is_capped():
    assert f.streak_multiplier(0) == 1
    assert f.streak_multiplier(5) == pytest.approx(1.1)
    assert f.streak_multiplier(100) == 1.3


def test_daily_cap():
    assert f.apply_daily_cap(100, 550) == 50
    assert f.apply_daily_cap(100, 700) == 0


def test_level_zero_rejected():
    with pytest.raises(ValueError):
        f.xp_to_next(0)


def test_timed_set_xp():
    from app.modules.gamification.formulas import timed_set_xp

    assert timed_set_xp(1800, "cardio") == 15  # 30 min x 0.5
    assert timed_set_xp(4 * 3600, "cardio") == 30  # capped per set
    assert timed_set_xp(30, "flexibility") == 1  # a short hold still counts
    assert timed_set_xp(600, "meditation") == 10  # 1 XP per calm minute
    assert timed_set_xp(3600, "meditation") == 20  # calm cap
    assert timed_set_xp(None, "cardio") == 0
