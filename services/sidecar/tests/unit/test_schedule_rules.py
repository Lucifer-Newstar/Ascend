"""schedule-v1: weekdays, the week view and the short session."""

from __future__ import annotations

from datetime import date

from app.modules.schedule import rules

MON = date(2026, 10, 26)


def test_days_round_trip_and_defaults() -> None:
    assert rules.parse_days("4,0,2,2,9,x") == (0, 2, 4)
    assert rules.format_days((4, 0, 2)) == "0,2,4"
    assert rules.default_days(3) == (0, 2, 4)
    assert rules.default_days(0) == (2,) and rules.default_days(9) == tuple(range(7))
    assert rules.days_label((0, 2, 4)) == "Mon, Wed, Fri"


def test_time_must_be_hh_mm() -> None:
    assert rules.valid_time("06:30") and rules.valid_time("23:59")
    for bad in ("24:00", "6:30", ""):
        assert not rules.valid_time(bad)


def test_week_view_lines_sessions_up_on_planned_days() -> None:
    wed = date(2026, 10, 28)
    view = rules.week_view(MON, (0, 2, 4), {MON}, ["Push", "Pull", "Legs"], wed)
    assert [d.planned for d in view] == [True, False, True, False, True, False, False]
    assert view[0].done and view[0].past and view[0].session is None
    assert view[2].today and view[2].session == "Push"
    assert view[4].session == "Pull"
    assert all(d.session is None for d in view if not d.planned)


def test_week_view_wraps_the_rotation() -> None:
    view = rules.week_view(MON, (0, 1, 2, 3), set(), ["A", "B"], MON)
    assert [d.session for d in view[:4]] == ["A", "B", "A", "B"]


def test_short_session_fits_ten_minutes() -> None:
    items = [("Push-up", 90, "reps"), ("Run", 0, "time"), ("Squat", 120, "reps"),
             ("Plank", 60, "hold"), ("Row", 90, "reps")]  # fmt: skip
    kept, minutes = rules.short_session(items, 10)
    assert [k.index for k in kept] == [0, 2, 3]
    assert all(k.sets == 2 and k.rest_s <= 45 for k in kept)
    assert minutes <= 10


def test_short_session_drops_moves_that_do_not_fit() -> None:
    items = [("A", 45, "reps")] * 5
    kept, minutes = rules.short_session(items, 5)
    assert len(kept) == 2 and minutes <= 5
    assert rules.short_session([("Run", 0, "time")], 10) == ([], 0)
