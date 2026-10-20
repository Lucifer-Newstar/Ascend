"""prog-v1 (E2) on hand-computed fixtures: double progression, increments by equipment,
RPE autoregulation, e1RM tracking, stall detection, holds and skill-tree targets."""

from datetime import datetime, timedelta

from app.modules.intelligence import progression as prog
from app.modules.intelligence.progression import ExerciseInfo, SessionRec, SetRec, SkillGoal

NOW = datetime(2026, 10, 20, 18, 0)
BENCH = ExerciseInfo("Barbell Bench Press", "barbell", "reps", "compound", "push", 6, 12)
SQUAT = ExerciseInfo("Back Squat", "barbell", "reps", "compound", "squat", 6, 12)
RAISE = ExerciseInfo("Lateral Raise", "dumbbell", "reps", "isolation", "push", 6, 12)
PULLUP = ExerciseInfo("Pull-up", "bodyweight", "reps", "compound", "pull", 6, 12)
PLANK = ExerciseInfo("Plank", "bodyweight", "hold", "isolation", "isometric", 10, 30)
LEVER = ExerciseInfo("Tuck Front Lever", "bar", "hold", None, "isometric", 10, 30)
RUN = ExerciseInfo("Running", "none", "time", None, "other")


def sess(days_ago: float, load: float, reps: list[int], rpe: float | None = 8.0) -> SessionRec:
    return SessionRec(NOW - timedelta(days=days_ago), tuple(SetRec(r, load, rpe) for r in reps))


def holds(days_ago: float, secs: list[int], load: float = 0.0, rpe: float | None = 8.0):
    return SessionRec(
        NOW - timedelta(days=days_ago),
        tuple(SetRec(1, load, rpe, duration_s=s) for s in secs),
    )


def test_first_time_has_no_numbers_yet() -> None:
    t = prog.next_target(BENCH, [], NOW)
    assert t.change == "first" and t.reps is None and t.rpe == 8.0


def test_add_a_rep_inside_the_range() -> None:
    t = prog.next_target(BENCH, [sess(3, 60, [8, 8, 7])], NOW)
    assert (t.change, t.reason) == ("up_reps", "add_rep")
    assert (t.weight_kg, t.reps, t.sets, t.rep_range) == (60, 8, 3, (6, 10))
    assert "aim for 8" in t.why


def test_top_of_range_adds_one_increment_and_resets_reps() -> None:
    t = prog.next_target(BENCH, [sess(3, 60, [10, 10, 10])], NOW)
    assert (t.change, t.reason, t.weight_kg, t.reps) == ("up_load", "top_of_range", 62.5, 6)
    assert "+2.5 kg" in t.why


def test_lower_body_barbell_adds_5_kg() -> None:
    t = prog.next_target(SQUAT, [sess(3, 100, [10, 10, 10])], NOW)
    assert t.weight_kg == 105 and t.increment_kg == 5.0


def test_small_dumbbells_add_reps_before_a_big_jump() -> None:
    # 2.5 kg on 8 kg is 31 %: reps go to 12 + 2 first
    t = prog.next_target(RAISE, [sess(3, 8, [12, 12, 12])], NOW)
    assert (t.reason, t.weight_kg, t.reps) == ("micro_reps", 8, 13)
    t2 = prog.next_target(RAISE, [sess(3, 8, [14, 14, 14])], NOW)
    assert t2.change == "up_load" and t2.weight_kg == 10.5
    # the jump keeps the e1RM demand level instead of resetting to 8 reps
    assert t2.reps is not None and 1 <= t2.reps < 14


def test_easy_sets_raise_the_load_from_e1rm_capped_at_10_percent() -> None:
    t = prog.next_target(BENCH, [sess(3, 60, [8, 8, 8], rpe=6.0)], NOW)
    assert t.reason == "too_easy"
    assert 60 < t.weight_kg <= 66
    assert t.reps == 8


def test_grinding_sets_repeat() -> None:
    t = prog.next_target(BENCH, [sess(3, 60, [8, 7, 7], rpe=10.0)], NOW)
    assert (t.change, t.reason, t.weight_kg, t.reps) == ("hold", "too_hard", 60, 7)


def test_under_the_range_once_then_twice() -> None:
    once = prog.next_target(BENCH, [sess(6, 60, [8, 8, 8]), sess(3, 62.5, [6, 5, 5])], NOW)
    assert (once.reason, once.weight_kg, once.reps) == ("below_range", 62.5, 6)
    twice = prog.next_target(
        BENCH, [sess(9, 60, [8, 8, 8]), sess(6, 62.5, [5, 5, 4]), sess(3, 62.5, [5, 5, 5])], NOW
    )
    assert twice.reason == "below_twice" and twice.change == "down"
    assert twice.weight_kg == 57.5  # 62.5 x 0.925 = 57.8, rounded down to 1.25 kg steps


def test_stall_after_three_flat_sessions_resets_ten_percent() -> None:
    # the first session sets the record; three more without beating it is a stall
    hist = [sess(30 - 3 * i, 80, [8, 8, 8]) for i in range(4)]
    t = prog.next_target(BENCH, hist, NOW)
    assert t.stall.stalled and t.stall.sessions_flat == 3
    # 80 x 0.9 = 72, rounded down to the 1.25 kg barbell step
    assert (t.change, t.reason, t.weight_kg) == ("reset", "stall_reset", 71.25)


def test_no_stall_while_still_progressing() -> None:
    hist = [sess(30 - 3 * i, 60 + 2.5 * i, [8, 8, 8]) for i in range(6)]
    assert prog.next_target(BENCH, hist, NOW).stall.stalled is False
    # one more rep at the same load is a record too (double progression)
    reps = [sess(30 - 3 * i, 60, [6 + i, 6 + i, 6 + i]) for i in range(5)]
    assert prog.next_target(BENCH, reps, NOW).stall.stalled is False


def test_a_rep_record_at_a_lower_load_does_not_count() -> None:
    hist = [sess(20, 80, [8, 8, 8])] + [sess(15 - 4 * i, 75, [8, 8, 8]) for i in range(3)]
    # 75 x 8 is dominated by 80 x 8, and 75 kg is not a drop of 7 % (new cycle)
    assert prog.next_target(BENCH, hist, NOW).stall.stalled is True


def test_a_load_drop_starts_a_new_cycle() -> None:
    flat = [sess(40 - 3 * i, 80, [8, 8, 8]) for i in range(6)]
    after = [sess(16 - 3 * i, 72.5, [8, 8, 8]) for i in range(3)]
    t = prog.next_target(BENCH, flat + after, NOW)
    assert t.stall.stalled is False and t.stall.cycle_sessions == 3


def test_e1rm_track_uses_rir() -> None:
    hist = [sess(21, 60, [8, 8, 8]), sess(14, 62.5, [8, 8, 8]), sess(7, 65, [8, 8, 8])]
    t = prog.next_target(BENCH, hist, NOW)
    assert t.e1rm is not None
    assert t.e1rm.last == round(65 * (1 + 10 / 30), 1)  # 8 reps + RIR 2
    assert t.e1rm.best == t.e1rm.last
    assert t.e1rm.trend_pct_week is not None and t.e1rm.trend_pct_week > 0


def test_rep_zone_follows_your_own_history() -> None:
    strength = prog.next_target(SQUAT, [sess(3, 120, [5, 5, 5])], NOW)
    assert strength.rep_range == (3, 6)
    high = prog.next_target(RAISE, [sess(3, 6, [15, 15, 15])], NOW)
    assert high.rep_range == (12, 20)
    own = ExerciseInfo("Leg Press", "machine", "reps", "compound", "squat", 10, 15)
    assert prog.next_target(own, [sess(3, 100, [10, 10, 10])], NOW).rep_range == (10, 15)


def test_holds_add_ten_percent_toward_the_top() -> None:
    t = prog.next_target(PLANK, [holds(2, [25, 25, 22])], NOW)
    assert (t.kind, t.change, t.seconds) == ("hold", "up_time", 24)
    top = prog.next_target(PLANK, [holds(2, [30, 30, 30])], NOW)
    assert top.change == "advance"


def test_skill_criterion_drives_calisthenics_targets() -> None:
    goal = SkillGoal("Muscle-up", "Chest-to-bar pull-up", 3, 8, False)
    t = prog.next_target(PULLUP, [sess(2, 0, [7, 7, 6])], NOW, skill=goal)
    assert (t.reason, t.reps, t.sets) == ("skill_step", 7, 3)
    assert "Muscle-up" in t.why
    met = SkillGoal("Muscle-up", "Chest-to-bar pull-up", 3, 8, False, sessions_met=1)
    t2 = prog.next_target(PULLUP, [sess(2, 0, [8, 8, 8])], NOW, skill=met)
    assert t2.reason == "criterion_confirm" and "unlocks Chest-to-bar pull-up" in t2.why


def test_skill_hold_criterion() -> None:
    goal = SkillGoal("Front lever", "Advanced tuck front lever", 3, 10, True)
    t = prog.next_target(LEVER, [holds(2, [8, 8, 7])], NOW, skill=goal)
    assert (t.seconds, t.reason) == (9, "add_time")
    assert "3x9 s" in t.why


def test_fatigued_muscles_hold_an_increase() -> None:
    t = prog.next_target(
        BENCH, [sess(1, 60, [10, 10, 10])], NOW, readiness=0.35, readiness_muscle="Lower chest"
    )
    assert (t.change, t.reason, t.weight_kg, t.reps) == ("hold", "hold_recovering", 60, 10)
    assert "35%" in t.why


def test_keep_mine_is_respected_for_seven_days() -> None:
    hist = [sess(3, 60, [10, 10, 10])]
    kept = prog.next_target(BENCH, hist, NOW, kept_at=NOW - timedelta(days=2))
    assert kept.reason == "kept" and kept.weight_kg == 60
    later = prog.next_target(BENCH, hist, NOW, kept_at=NOW - timedelta(days=8))
    assert later.reason == "top_of_range"


def test_timed_activities_get_no_target() -> None:
    assert prog.next_target(RUN, [], NOW).kind == "none"


def test_warm_ups_are_not_working_sets() -> None:
    s = SessionRec(
        NOW - timedelta(days=3),
        (SetRec(10, 20, None), SetRec(5, 40, None), SetRec(8, 60, 8), SetRec(8, 60, 8)),
    )
    t = prog.next_target(BENCH, [s], NOW)
    assert t.sets == 2 and t.inputs["last_sets"] == "8, 8"


def test_bodyweight_above_the_top_never_gets_a_lower_target() -> None:
    # 22 bodyweight reps is above the 12-20 zone: the next target is 23, not 21
    pushup = ExerciseInfo("X", "bodyweight", "reps", "compound", "push")
    hist = [SessionRec(NOW - timedelta(days=1), (SetRec(22, 0.0, None),))]
    t = prog.next_target(pushup, hist, NOW)
    assert (t.reason, t.reps) == ("top_no_load", 23)
    held = prog.next_target(pushup, hist, NOW, readiness=0.0)
    assert held.reason == "hold_recovering" and held.reps == 22
    capped = [SessionRec(NOW - timedelta(days=1), (SetRec(35, 0.0, None),))]
    assert prog.next_target(pushup, capped, NOW).reps == 35
