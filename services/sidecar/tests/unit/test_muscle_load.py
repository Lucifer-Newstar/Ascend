from datetime import datetime, timedelta

import pytest

from app.modules.progress.muscle_load import (
    Contribution,
    compute_states,
    decayed,
    effort,
    worst_status,
)

NOW = datetime(2026, 10, 20, 18, 0)


def state(states, key):
    return next(s for s in states if s.key == key)


@pytest.mark.parametrize("rpe,expected", [(None, 1.0), (9, 1.0), (7, 1.0), (6, 0.5), (4, 0.25)])
def test_effort_bands(rpe, expected):
    assert effort(rpe) == expected


def test_decay_matches_plan_worked_example():
    # 4.0 ES, 68 h later, 36 h half-life -> ~1.1 ES left
    assert decayed(4.0, 68, 36) == pytest.approx(1.08, abs=0.01)


def test_no_data_when_nothing_logged():
    states = compute_states([], NOW)
    assert all(s.status == "no_data" for s in states)
    assert len(states) == 19


def test_hard_session_yesterday_is_recovering():
    c = [Contribution("quads", 1.0, NOW - timedelta(hours=12)) for _ in range(8)]
    quads = state(compute_states(c, NOW), "quads")
    assert quads.status == "recovering"
    assert quads.readiness < 0.7
    assert quads.ready_at is not None and quads.ready_at > NOW


def test_light_old_volume_is_under():
    c = [Contribution("biceps", 1.0, NOW - timedelta(days=5))]
    assert state(compute_states(c, NOW), "biceps").status == "under"


def test_volume_inside_band_and_recovered_is_optimal():
    c = [
        Contribution("biceps", 1.0, NOW - timedelta(days=d, hours=1))
        for d in range(1, 6)
        for _ in range(2)
    ]
    assert state(compute_states(c, NOW), "biceps").status == "optimal"


def test_too_much_weekly_volume_is_over():
    c = [
        Contribution("calves", 1.0, NOW - timedelta(days=d)) for d in range(1, 7) for _ in range(3)
    ]
    assert state(compute_states(c, NOW), "calves").status == "over"


def test_worst_status_precedence():
    assert worst_status(["optimal", "recovering", "under"]) == "recovering"
    assert worst_status(["over", "recovering"]) == "over"
    assert worst_status([]) == "no_data"
