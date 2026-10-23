from datetime import date, timedelta

from app.modules.gamification.streaks import compute_streak

TODAY = date(2026, 10, 20)


def days_back(*offsets):
    return [TODAY - timedelta(days=o) for o in offsets]


def day(o):
    return TODAY - timedelta(days=o)


def test_empty_history():
    s = compute_streak([], TODAY)
    assert s.current == 0 and s.best == 0


def test_consecutive_days_including_today():
    s = compute_streak(days_back(0, 1, 2), TODAY)
    assert s.current == 3 and s.active_today


def test_today_not_yet_active_does_not_break():
    s = compute_streak(days_back(1, 2), TODAY)
    assert s.current == 2 and not s.active_today


def test_missed_day_without_reason_resets_once_the_next_day_is_over():
    s = compute_streak(days_back(0, 1, 3, 4, 5), TODAY)
    assert s.current == 2
    assert s.best == 3
    assert s.reason_due is None


def test_yesterday_missed_waits_for_a_reason_today():
    s = compute_streak(days_back(2, 3, 4), TODAY)
    assert s.current == 3
    assert s.reason_due == day(1)


def test_a_reason_by_the_next_day_keeps_the_streak():
    # active 3..5, missed day 2 (reason given on day 1 = the next day), active 1 and 0
    s = compute_streak(days_back(5, 4, 3, 1, 0), TODAY, {day(2): day(1)})
    assert s.current == 5  # the excused day does not add
    assert s.excused == 1
    assert s.reason_due is None


def test_a_late_reason_does_not_count():
    s = compute_streak(days_back(5, 4, 3, 1, 0), TODAY, {day(2): day(0)})
    assert s.current == 2
    assert s.excused == 0


def test_two_missed_days_in_a_row_reset_even_with_reasons():
    reasons = {day(3): day(2), day(2): day(1)}
    s = compute_streak(days_back(6, 5, 4, 1, 0), TODAY, reasons)
    assert s.current == 2
    assert s.best == 3


def test_there_are_no_freezes_any_more():
    s = compute_streak(days_back(*range(3, 10)) + days_back(1, 0), TODAY)
    assert s.current == 2  # a 7-day run no longer earns a freeze that covers day 2
