from datetime import date, timedelta

from app.modules.gamification.streaks import compute_streak

TODAY = date(2026, 10, 20)


def days_back(*offsets):
    return [TODAY - timedelta(days=o) for o in offsets]


def test_empty_history():
    s = compute_streak([], TODAY)
    assert s.current == 0 and s.best == 0


def test_consecutive_days_including_today():
    s = compute_streak(days_back(0, 1, 2), TODAY)
    assert s.current == 3 and s.active_today


def test_today_not_yet_active_does_not_break():
    s = compute_streak(days_back(1, 2), TODAY)
    assert s.current == 2 and not s.active_today


def test_gap_without_freeze_resets():
    s = compute_streak(days_back(0, 2, 3), TODAY)
    assert s.current == 1
    assert s.best == 2


def test_seven_day_run_earns_freeze_that_covers_a_miss():
    # 7 active days, one miss, then yesterday and today
    history = days_back(*range(3, 10)) + days_back(1, 0)
    s = compute_streak(history, TODAY)
    assert s.freezes_used == 1
    assert s.current == 9


def test_freezes_cap_at_two():
    s = compute_streak(days_back(*range(0, 30)), TODAY)
    assert s.freezes_held == 2
    assert s.current == 30
