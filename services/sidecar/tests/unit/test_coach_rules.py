from datetime import datetime, timedelta

from app.modules.coach.rules import CoachContext, rule_tip
from app.modules.progress.muscle_load import Contribution, compute_states

NOW = datetime(2026, 10, 20, 19, 0)


def ctx(**over):
    base = dict(
        now=NOW,
        has_profile=True,
        muscles=compute_states([], NOW),
        kcal_eaten=0,
        kcal_target=2500,
        protein_g=0,
        protein_target_g=110,
        streak=0,
        active_today=False,
        sets_today=0,
    )
    base.update(over)
    return CoachContext(**base)


def test_onboarding_first():
    assert rule_tip(ctx(has_profile=False)).code == "onboard"


def test_overreaching_beats_everything():
    c = [
        Contribution("calves", 1.0, NOW - timedelta(days=d)) for d in range(1, 7) for _ in range(3)
    ]
    assert rule_tip(ctx(muscles=compute_states(c, NOW))).code == "over"


def test_under_muscles_suggested_when_nothing_trained_today():
    c = [Contribution("biceps", 1.0, NOW - timedelta(days=3))]
    assert rule_tip(ctx(muscles=compute_states(c, NOW))).code == "under"


def test_protein_gap_in_the_evening():
    assert rule_tip(ctx(protein_g=20, sets_today=3)).code == "protein"


def test_streak_reminder():
    assert rule_tip(ctx(streak=5, protein_g=100, sets_today=0)).code == "streak"


def test_deterministic():
    assert rule_tip(ctx()) == rule_tip(ctx())
