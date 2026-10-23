"""boss-v1 (ADR-0022): the weekly boss raid is deterministic."""

from datetime import date, timedelta

from app.modules.gamification import boss

MON = date(2026, 10, 19)


def test_week_starts_on_monday_and_the_boss_rotates():
    assert boss.week_start(date(2026, 10, 25)) == MON  # Sunday
    assert boss.week_start(MON) == MON
    assert boss.boss_for(MON) == boss.boss_for(MON)
    names = {boss.boss_for(MON + timedelta(weeks=n))[0] for n in range(len(boss.BOSSES))}
    assert len(names) == len(boss.BOSSES)  # every boss once per rotation


def test_hp_prefers_the_program_then_history_then_a_starter():
    p = boss.hp_for(60, "Push / pull / legs", False, [10, 20, 30, 40])
    assert (p.hp, p.source) == (60, "program")
    assert boss.hp_for(60, "Push / pull / legs", True, []).hp == 30  # deload week: halved
    h = boss.hp_for(None, None, False, [0, 22, 30, 26])
    assert (h.hp, h.source) == (24, "history")  # median of 0, 22, 26, 30
    assert "22, 30, 26" in h.note
    assert boss.hp_for(None, None, False, [0, 0, 0, 0]) == boss.Hp(20, "starter", h_starter())
    assert boss.hp_for(None, None, False, [400, 400]).hp == boss.HP_MAX
    assert boss.hp_for(None, None, False, [1, 2]).hp == boss.HP_MIN


def h_starter() -> str:
    return boss.hp_for(None, None, False, []).note


def test_each_set_deals_one_damage_and_the_boss_falls_on_the_set_that_empties_it():
    days = [MON] * 5 + [MON + timedelta(days=2)] * 5 + [MON + timedelta(days=4)] * 5
    assert boss.outcome(12, days) == boss.Outcome(15, MON + timedelta(days=4))
    assert boss.outcome(10, days).defeated_on == MON + timedelta(days=2)
    assert boss.outcome(16, days) == boss.Outcome(15, None)


# --- boss-v2 (v1.2): tiers and seasons ----------------------------------------------------


def test_every_boss_has_a_tier_and_a_category_and_the_ladder_climbs():
    for name, _ in boss.BOSSES:
        assert boss.BOSS_TIER[name] in boss.TIERS
        assert boss.BOSS_CATEGORY[name] in ("strength", "calisthenics", "cardio", "martial_arts")
    assert boss.BOSS_TIER["Bone Titan"] == "S"
    scales = [boss.TIER_HP_SCALE[t] for t in boss.TIERS]
    bonuses = [boss.TIER_BONUS_XP[t] for t in boss.TIERS]
    assert scales == sorted(scales) and bonuses == sorted(bonuses)
    hp = boss.Hp(40, "history", "median")
    assert boss.scaled(hp, "E").hp == 32 and boss.scaled(hp, "S").hp == 52
    assert boss.scaled(hp, "C") == hp


def test_each_season_has_its_boss_every_other_week():
    assert [s.boss for s in boss.SEASONS] == [
        "Winter Wraith",
        "Shadow Sovereign",
        "Monsoon Serpent",
        "Harvest Colossus",
    ]
    months = sorted(m for s in boss.SEASONS for m in s.months)
    assert months == list(range(1, 13))  # one season at a time, all year
    first = boss.season_start(date(2026, 10, 19))
    assert first == date(2026, 10, 5)  # the first Monday of October
    assert boss.season_end(date(2026, 10, 19)) == date(2026, 11, 30)
    weeks = [first + timedelta(weeks=n) for n in range(6)]
    assert [boss.seasonal_week(w) for w in weeks] == [True, False, True, False, True, False]
    assert boss.boss_for(first, "beginner", seasonal=True)[0] == "Harvest Colossus"
    # never on a low-readiness day, and never without the seasonal flag
    assert (
        boss.boss_for(first, "beginner", low_readiness=True, seasonal=True)[0] != "Harvest Colossus"
    )
    assert boss.boss_for(first, "beginner")[0] != "Harvest Colossus"


def test_a_seasonal_boss_follows_your_level():
    assert boss.tier_of("Winter Wraith", "beginner") == "D"
    assert boss.tier_of("Winter Wraith", "expert") == "S"
    assert boss.tier_of("Iron Golem", "expert") == "E"  # regular bosses keep their own tier
    assert boss.category_of("Harvest Colossus") == "martial_arts"


def test_winter_runs_across_the_new_year():
    jan = date(2027, 1, 11)
    assert boss.season_for(jan).boss == "Winter Wraith"
    assert boss.season_start(jan) == date(2026, 12, 7)  # the first Monday of December
    assert boss.season_end(jan) == date(2027, 2, 28)
    assert boss.season_start(date(2026, 12, 14)) == date(2026, 12, 7)
    assert boss.season_for(date(2027, 3, 1)).boss == "Shadow Sovereign"


def test_tier_bonus_and_unknown_names_have_safe_defaults():
    assert [boss.bonus_for(t) for t in boss.TIERS] == [100, 125, 150, 175, 200, 250]
    assert boss.bonus_for("?") == boss.BONUS_XP
    assert boss.tier_of("Someone New") == "C" and boss.category_of("Someone New") == "strength"
    assert boss.tier_of("Harvest Colossus") == "D"  # no level yet: the beginner tier
    big = boss.Hp(140, "program", "x")
    assert boss.scaled(big, "S").hp == boss.HP_MAX  # the tier never breaks the HP cap
    small = boss.Hp(12, "starter", "x")
    assert boss.scaled(small, "E").hp == boss.HP_MIN
