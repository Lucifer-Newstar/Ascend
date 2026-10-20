import itertools
from datetime import datetime, timedelta

from app.modules.skills import engine
from app.modules.skills.catalog import SKILL_BY_KEY, SKILLS, C

NOW = datetime(2026, 10, 20, 18, 0)


_ids = itertools.count(1)


def rec(exercise, days_ago, *, reps=1, hold=None, kg=0.0):
    return engine.SetRecord(next(_ids), exercise, NOW - timedelta(days=days_ago), reps, hold, kg)


def test_session_score_averages_the_best_sets():
    rs = [rec("Pull-up", 1, reps=8), rec("Pull-up", 1, reps=8), rec("Pull-up", 1, reps=6)]
    res = engine.evaluate_criterion(C("Pull-up", 3, 8), rs, NOW)
    assert round(res.best_score, 3) == round((1 + 1 + 0.75) / 3, 3)
    assert res.best_value == 8 and res.sessions_met == 0 and not res.met
    assert res.pct == round(90 * res.best_score, 1)


def test_two_qualifying_sessions_are_needed_to_unlock():
    day1 = [rec("Dead Hang", 3, hold=30) for _ in range(3)]
    res = engine.evaluate_criterion(C("Dead Hang", 3, hold=30), day1, NOW)
    assert res.sessions_met == 1 and not res.met and res.pct == 95.0
    day2 = [rec("Dead Hang", 1, hold=31) for _ in range(3)]
    res = engine.evaluate_criterion(C("Dead Hang", 3, hold=30), day1 + day2, NOW)
    assert res.met and res.pct == 100.0 and len(res.evidence) == 6


def test_old_sessions_fall_out_of_the_window():
    old = [rec("Pull-up", engine.WINDOW_DAYS + 2, reps=10) for _ in range(3)]
    res = engine.evaluate_criterion(C("Pull-up", 3, 8), old, NOW)
    assert res.best_score == 0 and res.best_value is None


def test_added_load_requirement_and_implausible_holds():
    light = [rec("Weighted Dip", 1, reps=5, kg=5) for _ in range(3)]
    assert engine.evaluate_criterion(C("Weighted Dip", 3, 5, kg=10), light, NOW).best_score == 0
    absurd = [rec("Front Lever", 1, hold=900)]
    res = engine.evaluate_criterion(C("Front Lever", 1, hold=5), absurd, NOW)
    assert res.ignored_sets == 1 and res.best_score == 0


def test_tree_state_entry_steps_next_step_and_unlock_flags():
    skill = SKILL_BY_KEY["muscle_up"]
    rs = [rec("Dead Hang", d, hold=30) for d in (3, 1) for _ in range(3)]
    res = engine.evaluate_skill(skill, rs, {}, NOW)
    assert res.steps[0].status == "unlocked"  # entry step
    assert res.next is not None and res.next.step.key == "scap_pull"
    assert res.next.eligible and res.next.pct == 100.0
    assert res.current is not None and res.current.key == "dead_hang"
    later = res.steps[3]
    assert later.status == "locked" and not later.eligible


def test_branching_step_needs_every_prerequisite():
    hs = SKILL_BY_KEY["handstand"]
    have = {k: NOW for k in ("headstand", "wall_hs", "elevated_pike", "wall_hspu")}
    res = engine.evaluate_skill(hs, [], have, NOW)
    free_hspu = next(s for s in res.steps if s.step.key == "free_hspu")
    assert free_hspu.status == "locked"  # free handstand not yet unlocked
    have["free_hs"] = NOW
    res = engine.evaluate_skill(hs, [], have, NOW)
    assert next(s for s in res.steps if s.step.key == "free_hspu").status == "next"


def test_eta_only_with_enough_sessions_and_an_upward_trend():
    c = C("Tuck Front Lever", 3, hold=15)
    few = [rec("Tuck Front Lever", 2, hold=8) for _ in range(3)]
    assert engine.criterion_eta(engine.evaluate_criterion(c, few, NOW)) is None
    rising = [
        rec("Tuck Front Lever", d, hold=h)
        for d, h in ((21, 6), (14, 8), (7, 10), (1, 12))
        for _ in range(3)
    ]
    eta = engine.criterion_eta(engine.evaluate_criterion(c, rising, NOW))
    assert eta is not None and 5 < eta < 60
    flat = [rec("Tuck Front Lever", d, hold=8) for d in (21, 14, 7, 1) for _ in range(3)]
    assert engine.criterion_eta(engine.evaluate_criterion(c, flat, NOW)) is None


def test_catalog_shape():
    assert len(SKILLS) == 12
    for skill in SKILLS:
        keys = [s.key for s in skill.steps]
        assert len(keys) == len(set(keys)), skill.key
        seen: set[str] = set()
        for step in skill.steps:
            assert all(r in seen for r in skill.requires_of(step)), (skill.key, step.key)
            seen.add(step.key)
            assert step.unlock or step is skill.steps[0], (skill.key, step.key)
            for c in step.unlock:
                assert c.sets >= 1 and c.target >= 1
        assert skill.sources and skill.feeders
