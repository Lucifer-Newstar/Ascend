"""v1.3 near goals: sub-ranks, session milestones and weeks in a row (pure helpers)."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.gamification import formulas as f
from app.modules.gamification.streaks import next_milestone, weeks_in_a_row

MON = date(2026, 11, 2)


def test_sub_ranks_split_each_rank_in_three() -> None:
    assert f.sub_rank_for_level(1) == ("E1", "E2", 4)
    assert f.sub_rank_for_level(4)[0] == "E2"
    assert f.sub_rank_for_level(7)[0] == "E3"
    assert f.sub_rank_for_level(9) == ("E3", "D1", 10)
    assert f.sub_rank_for_level(10)[0] == "D1"
    assert f.sub_rank_for_level(49)[0] == "B3"
    assert f.sub_rank_for_level(70) == ("S1", "S2", 80)
    assert f.sub_rank_for_level(95) == ("S3", None, None)


def test_sub_ranks_never_disagree_with_the_rank_letter() -> None:
    for level in range(1, 120):
        assert f.sub_rank_for_level(level)[0][0] == f.rank_for_level(level)[0], level


def test_session_milestones() -> None:
    assert next_milestone(0) == 1
    assert next_milestone(1) == 3
    assert next_milestone(9) == 10
    assert next_milestone(99) == 100
    assert next_milestone(100) is None


def test_weeks_in_a_row_counts_back_from_the_last_met_week() -> None:
    weeks = [MON - timedelta(days=7 * k) for k in range(1, 4)]  # 3 weeks before this one
    assert weeks_in_a_row(weeks, MON + timedelta(days=2)) == 3  # this week still going
    assert weeks_in_a_row([*weeks, MON], MON + timedelta(days=2)) == 4
    gap = [MON - timedelta(days=7), MON - timedelta(days=21)]
    assert weeks_in_a_row(gap, MON) == 1
    assert weeks_in_a_row([], MON) == 0
