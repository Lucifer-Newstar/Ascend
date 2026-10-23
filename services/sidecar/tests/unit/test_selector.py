"""select-v1: table-driven eligibility, safety gates, cooldowns and caps."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.modules.gamification import boss
from app.modules.selector import catalog, engine
from app.modules.selector.state import (
    LEVELS,
    PlayerState,
    StrengthRatios,
    experience_level,
    level_rank,
)

TODAY = date(2026, 10, 23)
BALANCED = {"push": 1.0, "pull": 1.0, "legs": 1.0, "core": 1.0, "cardio": 1.0, "calisthenics": 1.0}


def state(**kw: object) -> PlayerState:
    base = PlayerState(
        level="beginner", game_level=3, age=21, training_weeks=10.0, sets_per_week=20.0,
        ratios=StrengthRatios(), load=dict(BALANCED), readiness=70, readiness_source="checkin",
        streak=0, days_since_workout=1, sessions_14d=6, planned_per_week=3, kcal_ratio=1.0,
        protein_ratio=1.0, meal_days_7d=7, goal="maintain", weight_trend_kg_week=0.0,
        trend_matches_goal=True,
    )  # fmt: skip
    return replace(base, **kw)  # type: ignore[arg-type]


def eligible(s: PlayerState) -> set[str]:
    return {i.id for i in catalog.ITEMS if engine.check(i, s).eligible}


@pytest.mark.parametrize(
    ("weeks", "sets", "ratios", "level"),
    [
        (0.5, 5, StrengthRatios(), "beginner"),
        (20, 35, StrengthRatios(), "intermediate"),
        (20, 10, StrengthRatios(squat=1.1), "intermediate"),
        (60, 20, StrengthRatios(bench=1.2), "advanced"),
        (60, 20, StrengthRatios(bench=1.0), "intermediate"),
        (120, 70, StrengthRatios(deadlift=2.6), "expert"),
        (120, 70, StrengthRatios(deadlift=2.0), "advanced"),
    ],
)
def test_experience_level(weeks: float, sets: float, ratios: StrengthRatios, level: str) -> None:
    assert experience_level(weeks, sets, ratios) == level


def test_without_a_log_the_self_reported_level_is_used() -> None:
    assert experience_level(0, 0, StrengthRatios(), "advanced", has_log=False) == "advanced"
    assert experience_level(0, 0, StrengthRatios(), None, has_log=False) == "beginner"


@pytest.mark.parametrize("level", LEVELS)
def test_no_item_above_or_below_its_levels(level: str) -> None:
    s = state(level=level, readiness=90)
    for item in catalog.ITEMS:
        if engine.check(item, s).eligible:
            assert level_rank(item.min_level) <= level_rank(level) <= level_rank(item.max_level)


def test_beginner_never_gets_expert_or_advanced_content() -> None:
    got = eligible(state(level="beginner", readiness=95))
    assert not got & {"plan_deloads", "expert_peaking", "hard_boss_push", "top_set_day"}
    assert {"plan_deloads", "hard_boss_push"} <= eligible(state(level="advanced", readiness=95))


@pytest.mark.parametrize("level", LEVELS)
def test_low_readiness_never_gets_hard_content(level: str) -> None:
    s = state(level=level, readiness=35)
    got = eligible(s)
    hard = {i.id for i in catalog.ITEMS if i.hard}
    assert not got & hard
    assert "rest_low_readiness" in got
    assert not any(boss.BOSS_GATES[n][0] in ("advanced", "expert")
                   for n, _ in boss.eligible_bosses(level, low_readiness=True))  # fmt: skip


def test_poor_diet_adherence_gets_nutrition_nudges() -> None:
    got = eligible(state(kcal_ratio=0.7, protein_ratio=0.6, meal_days_7d=5))
    assert {"eat_enough", "protein_nudge"} <= got
    assert "log_meals" in eligible(state(meal_days_7d=0))


@pytest.mark.parametrize(
    ("kw", "allowed"),
    [
        ({"goal": "cut", "kcal_ratio": 1.3, "age": 25}, True),
        ({"goal": "cut", "kcal_ratio": 1.3, "age": 16}, False),  # under 18: never a deficit nudge
        ({"goal": "cut", "kcal_ratio": 0.8, "age": 25}, False),  # intake already low
    ],
)
def test_deficit_items_are_gated(kw: dict[str, object], allowed: bool) -> None:
    v = engine.check(catalog.ITEM_BY_ID["trim_portions"], state(**kw))
    if allowed:
        assert v.eligible
    else:
        assert not v.eligible


def test_why_quotes_the_numbers() -> None:
    s = state(load={**BALANCED, "legs": 0.4})
    v = engine.check(catalog.ITEM_BY_ID["legs_under"], s)
    assert v.eligible and v.why == ["your legs volume is 60% under this week's target"]
    pick = engine.select(s, [catalog.ITEM_BY_ID["legs_under"]], {}, TODAY)[0]
    assert pick.text.startswith("Legs are at 40% of this week's target")


def test_cooldowns_are_respected() -> None:
    item = catalog.ITEM_BY_ID["legs_under"]  # cooldown 3 days
    s = state(load={**BALANCED, "legs": 0.4})
    assert engine.select(s, [item], {item.id: TODAY - timedelta(days=1)}, TODAY) == []
    assert engine.select(s, [item], {item.id: TODAY - timedelta(days=3)}, TODAY)


def test_daily_and_kind_caps_and_one_per_category() -> None:
    s = state(load={**BALANCED, "legs": 0.2, "push": 0.2, "pull": 0.2, "core": 0.2},
              kcal_ratio=0.6, protein_ratio=0.5, readiness=30)  # fmt: skip
    picks = engine.select(s, catalog.ITEMS, {}, TODAY)
    assert len(picks) == engine.DAILY_CAP
    kinds = [p.item.kind for p in picks]
    assert all(kinds.count(k) <= engine.KIND_CAP[k] for k in set(kinds))
    assert picks[0].item.id == "rest_low_readiness"  # safety first
    # The watcher's posts today count toward the same cap.
    assert (
        engine.select(s, catalog.ITEMS, {}, TODAY, {"pr": 2})
        and len(engine.select(s, catalog.ITEMS, {}, TODAY, {"pr": 2})) == 1
    )
    assert engine.select(s, catalog.ITEMS, {}, TODAY, {"pr": 3}) == []


def test_boss_gating_by_level_and_category() -> None:
    week = date(2026, 10, 19)
    for level in LEVELS:
        name, _ = boss.boss_for(week, level)
        assert level_rank(boss.BOSS_GATES[name][0]) <= level_rank(level)
    assert len(boss.eligible_bosses("beginner")) == 4
    assert len(boss.eligible_bosses("expert")) == 12
    name, _ = boss.boss_for(week, "intermediate", under="calisthenics")
    assert name == "Obsidian Hydra"
    assert boss.boss_for(week) == boss.BOSSES[(week.toordinal() // 7) % 12]
