"""programs-v1: the catalog is consistent with the library, and the next session follows the
rotation through missed days and extra workouts."""

from datetime import date, timedelta

import pytest

from app.modules.workouts import programs as pg
from app.modules.workouts.calisthenics_seed import CALISTHENICS
from app.modules.workouts.library import fedb_entries
from app.modules.workouts.seed import EXERCISES

LIBRARY = (
    {name for name, _, _ in EXERCISES}
    | {c["name"] for c in CALISTHENICS}
    | {e.name for e in fedb_entries()}
)
HOLDS = {c["name"] for c in CALISTHENICS if c["measure"] == "hold"} | {
    e.name for e in fedb_entries() if e.measure == "hold"
}
START = date(2026, 10, 5)  # a Monday


def names(p: pg.Program, i: int) -> set[str]:
    return {s.exercise for s in p.days[i].slots}


@pytest.mark.parametrize("key", sorted(pg.PROGRAMS))
def test_every_program_uses_library_exercises_and_sane_slots(key: str) -> None:
    p = pg.PROGRAMS[key]
    assert p.key == key and 3 <= p.days_per_week <= 6
    for d in p.days:
        assert 0 <= d.weekday <= 6
        for s in d.slots:
            assert s.exercise in LIBRARY, s.exercise
            top = 120 if s.exercise in HOLDS else 20  # v1.2: holds are dosed in seconds
            assert 1 <= s.sets <= 5 and 1 <= s.rep_low <= s.rep_high <= top
    assert len({d.weekday for d in p.days}) == p.days_per_week
    assert len({d.key for d in p.days}) == p.days_per_week


def test_first_session_is_day_one() -> None:
    p = pg.PROGRAMS["upper_lower_4"]
    s = pg.plan_state(p, START, [], START)
    assert s.next_index == 0 and s.sessions_done == 0
    assert s.reason == "first session of the program: Upper A"


def test_rotation_advances_on_matching_workouts_and_survives_missed_days() -> None:
    p = pg.PROGRAMS["upper_lower_4"]
    log = [(START, names(p, 0)), (START + timedelta(days=1), names(p, 1))]
    # A whole week missed, then back: the plan resumes with Upper B, nothing skipped.
    today = START + timedelta(days=10)
    s = pg.plan_state(p, START, log, today)
    assert s.next_index == 2 and s.sessions_done == 2 and s.this_week_done == 0
    assert "Lower A" in s.reason and "Upper B is next" in s.reason


def test_a_partial_session_counts_when_it_covers_half_the_day() -> None:
    p = pg.PROGRAMS["upper_lower_4"]
    half = set(sorted(names(p, 0))[:3])  # 3 of 6
    assert pg.match_day(p, half, 0) == 0
    assert pg.match_day(p, set(sorted(names(p, 0))[:2]), 0) is None


def test_an_unrelated_workout_does_not_advance_the_plan() -> None:
    p = pg.PROGRAMS["full_body_3"]
    log = [(START, {"Barbell Curl", "Hammer Curl"})]
    assert pg.plan_state(p, START, log, START).next_index == 0


def test_training_another_day_out_of_order_moves_the_rotation_on_from_it() -> None:
    p = pg.PROGRAMS["upper_lower_4"]
    s = pg.plan_state(p, START, [(START, names(p, 1))], START)  # did Lower A first
    assert s.next_index == 2


def test_identical_days_tie_to_the_day_that_was_due() -> None:
    p = pg.PROGRAMS["full_body_3"]  # days 0 and 2 are both "Full body A"
    log = [(START, names(p, 0)), (START + timedelta(days=2), names(p, 1))]
    s = pg.plan_state(p, START, log, START + timedelta(days=4))
    assert s.next_index == 2
    log.append((START + timedelta(days=4), names(p, 2)))
    assert pg.plan_state(p, START, log, START + timedelta(days=5)).next_index == 0


def test_workouts_before_the_start_or_in_the_future_are_ignored() -> None:
    p = pg.PROGRAMS["full_body_3"]
    log = [(START - timedelta(days=1), names(p, 0)), (START + timedelta(days=3), names(p, 0))]
    s = pg.plan_state(p, START, log, START + timedelta(days=1))
    assert s.sessions_done == 0


def test_target_text_uses_the_program_sets_with_prog_v1_reps_and_load() -> None:
    from app.modules.intelligence import progression as prog
    from app.modules.workouts.programs_service import target_text

    t = prog.Target(
        "reps", 3, 8, None, 62.5, 8.0, "hold", "", "", "", {}, (6, 10), 2.5, None,
        prog.Stall(False, 0, None, 0),
    )  # fmt: skip
    assert target_text(t, 4) == "4 × 8 @ 62.5 kg, RPE 8"
    no_history = prog.Target(
        "reps", 3, None, None, 0.0, None, "start", "", "", "", {}, (6, 10), 2.5, None,
        prog.Stall(False, 0, None, 0),
    )  # fmt: skip
    assert target_text(no_history, 4) is None
