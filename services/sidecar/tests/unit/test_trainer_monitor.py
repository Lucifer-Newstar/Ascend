"""watch-v1: the trainer notices events, each with a stable key."""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.trainer.monitor import Facts, watch

TODAY = date(2026, 10, 23)


def kinds(f: Facts) -> list[str]:
    return [n.kind for n in watch(f)]


def test_missed_sessions_after_the_expected_gap() -> None:
    f = Facts(TODAY, True, TODAY - timedelta(days=30), 3, TODAY - timedelta(days=5), 10)
    notes = watch(f)
    assert [n.kind for n in notes] == ["missed"]
    assert notes[0].key == f"missed:{(TODAY - timedelta(days=5)).isoformat()}"
    assert "5 days" in notes[0].text
    assert kinds(Facts(TODAY, True, None, 3, TODAY - timedelta(days=2), 10)) == []


def test_first_session_nudge_and_photo_reminder() -> None:
    f = Facts(TODAY, True, TODAY - timedelta(days=8), photos_supported=True)
    assert kinds(f) == ["missed", "photo_reminder"]
    f2 = Facts(TODAY, True, TODAY - timedelta(days=60), last_workout=TODAY,
               photos_supported=True, last_photo=TODAY - timedelta(days=10))  # fmt: skip
    assert "photo_reminder" not in kinds(f2)


def test_milestones_prs_skills_and_boss_are_shareable() -> None:
    f = Facts(
        TODAY,
        True,
        last_workout=TODAY,
        streak=7,
        prs=[(41, "Back Squat", 102.5, TODAY)],
        unlocks=[(3, "Muscle-up", "Pull-up", TODAY)],
        boss=(TODAY - timedelta(days=4), "Iron Golem", "Golem Breaker"),
    )
    notes = watch(f)
    assert [n.kind for n in notes] == ["pr", "skill", "boss", "streak"]
    assert all(n.action_kind == "share" for n in notes)
    assert notes[0].share == {"kind": "pr", "exercise": "Back Squat", "e1rm_kg": 102.5}


def test_overtraining_plateau_and_fast_loss() -> None:
    weights = [(TODAY - timedelta(days=d), 80 - (14 - d) * 0.2) for d in (14, 10, 7, 3, 0)]
    f = Facts(
        TODAY,
        True,
        last_workout=TODAY,
        over_muscles=["quads", "glutes"],
        stalled=["Bench Press"],
        weights=weights,
        goal="cut",
    )
    notes = {n.kind: n for n in watch(f)}
    assert set(notes) == {"overtraining", "plateau", "weight_trend"}
    assert notes["weight_trend"].mood == "warning"
    assert "1.4 kg a week" in notes["weight_trend"].text
