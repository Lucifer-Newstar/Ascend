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
