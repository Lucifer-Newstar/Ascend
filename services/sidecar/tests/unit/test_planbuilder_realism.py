from app.modules.planbuilder.realism import check


def test_eight_kilos_in_a_month_is_flagged_with_realistic_and_stretch_targets():
    c = check(42, 50, 4)
    assert not c.ok
    assert "2.0 kg a week" in c.message and "won't plan it" in c.message
    assert (c.realistic_kg, c.stretch_kg) == (43.0, 44.0)
    assert "body fat" not in c.message


def test_no_time_frame_gives_the_healthy_timeline():
    c = check(42, 50, None)
    assert c.ok
    assert "16-32 weeks" in c.message
    assert "45 kg in 6 weeks" in c.message


def test_steady_and_fast_paces():
    assert check(60, 62, 8).ok
    fast = check(60, 63, 4)
    assert fast.ok and "fast side" in fast.message
    assert not check(80, 70, 4).ok  # 2.5 kg a week down is flagged too
