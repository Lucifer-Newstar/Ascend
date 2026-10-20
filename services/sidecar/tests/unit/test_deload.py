from app.modules.workouts.deload import DeloadInputs, LiftTrend, advise, consecutive_training_weeks


def inputs(**kw):
    base = dict(
        weekly_sessions=[3, 3],
        readiness_7d=[75, 80, 72],
        soreness_7d=["none", "some", "none"],
        lifts=[LiftTrend("Back Squat", 120, 118), LiftTrend("Barbell Bench Press", 90, 89)],
        strained_muscles=0,
    )
    base.update(kw)
    return DeloadInputs(**base)


def test_fresh_lifter_needs_no_deload():
    a = advise(inputs())
    assert (a.recommended, a.kind, a.guidance) == (False, "none", None)
    assert [s.code for s in a.signals] == [
        "LOW_READINESS",
        "HEAVY_SORENESS",
        "PERFORMANCE_DROP",
        "FATIGUE_BUILDUP",
    ]


def test_planned_deload_after_three_training_weeks():
    a = advise(inputs(weekly_sessions=[1, 3, 4, 3]))
    assert (a.recommended, a.kind, a.training_weeks) == (True, "planned", 3)
    assert "half" in (a.guidance or "")


def test_a_light_week_resets_the_block():
    assert consecutive_training_weeks([3, 3, 1, 3]) == 1


def test_one_signal_is_not_enough():
    a = advise(inputs(readiness_7d=[40, 45, 42]))
    assert a.kind == "none"
    assert sum(s.active for s in a.signals) == 1


def test_two_signals_trigger_a_reactive_deload():
    a = advise(
        inputs(
            readiness_7d=[40, 45, 42, 48],
            lifts=[LiftTrend("Back Squat", 110, 120), LiftTrend("Deadlift", 140, 150)],
        )
    )
    assert (a.recommended, a.kind) == (True, "reactive")
    active = {s.code for s in a.signals if s.active}
    assert active == {"LOW_READINESS", "PERFORMANCE_DROP"}
    drop = next(s for s in a.signals if s.code == "PERFORMANCE_DROP")
    assert drop.detail == "e1RM down 3% or more on Back Squat, Deadlift"


def test_signal_wording_reads_as_a_sentence_when_nothing_dropped():
    drop = next(s for s in advise(inputs()).signals if s.code == "PERFORMANCE_DROP")
    assert drop.detail == "No key lift has dropped 3% or more in e1RM"


def test_soreness_plus_fatigue_also_trigger():
    a = advise(inputs(soreness_7d=["a_lot"] * 3, strained_muscles=4))
    assert a.kind == "reactive"


def test_low_readiness_needs_three_checkins():
    a = advise(inputs(readiness_7d=[20, 25], strained_muscles=5))
    assert a.kind == "none"


def test_active_deload_week_is_reported_not_re_recommended():
    a = advise(inputs(weekly_sessions=[3, 3, 3], in_deload_week=True))
    assert (a.recommended, a.kind) == (False, "active")
