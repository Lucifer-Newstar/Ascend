"""Weekly recap (v1.2): the first slide's line is kind and never about the body."""

from __future__ import annotations

from datetime import date

from app.modules.progress import recap

BODY = ("weight", "kg lost", "fat", "slim", "body")


def _r(**over) -> recap.WeekRecap:
    base = dict(
        week_start=date(2026, 10, 19),
        week_end=date(2026, 10, 25),
        complete=True,
        sessions=3,
        active_days=3,
        sets=30,
        active_minutes=120.0,
        volume_kg=4000.0,
        xp=600,
        prs=[],
        sections=[],
        best_day=None,
        boss=None,
        streak=5,
        excused_days=0,
        meal_days=4,
        checkins=3,
        level=12,
        rank="D",
        rank_title="Striver",
        last_week_sessions=2,
        last_week_sets=20,
        headline="",
    )
    base.update(over)
    return recap.WeekRecap(**base)


def test_the_headline_picks_the_best_thing_that_happened():
    boss = recap.RecapBoss(name="Iron Golem", title="Golem Breaker", tier="E", defeated=True)
    pr = recap.RecapPr(exercise="Pull-up", weight_kg=0, reps=8)
    assert recap.headline(_r(sessions=0)).startswith("A quiet week")
    assert "Iron Golem" in recap.headline(_r(boss=boss, prs=[pr]))
    assert recap.headline(_r(prs=[pr])).startswith("1 new personal record")
    assert recap.headline(_r()) == "3 sessions, up from 2 last week. Nice climb."
    assert recap.headline(_r(sessions=1, last_week_sessions=4)).startswith("1 session logged")


def test_no_headline_talks_about_the_body():
    boss = recap.RecapBoss(name="Iron Golem", title="x", tier="E", defeated=True)
    cases = [_r(sessions=0), _r(boss=boss), _r(), _r(sessions=1, last_week_sessions=0)]
    for c in cases:
        line = recap.headline(c).lower()
        assert not any(w in line for w in BODY), line
