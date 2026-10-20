from datetime import date, datetime, timedelta

from app.modules.progress import trend

T0 = datetime(2026, 10, 1, 7, 0)


def series(start, per_day, days, noise=()):
    pts = []
    for i in range(days):
        jitter = noise[i % len(noise)] if noise else 0.0
        pts.append((T0 + timedelta(days=i), round(start + per_day * i + jitter, 2)))
    return pts


def test_first_point_is_its_own_trend_and_moves_ten_percent():
    pts = [(T0, 70.0), (T0 + timedelta(days=1), 71.0)]
    assert trend.smooth(pts) == [70.0, 70.1]


def test_gap_applies_daily_smoothing_once_per_day():
    pts = [(T0, 70.0), (T0 + timedelta(days=7), 71.0)]
    # 1 - 0.9^7 = 0.5217
    assert trend.smooth(pts)[-1] == round(70 + 0.5217031 * 1.0, 2)


def test_slope_of_a_clean_line():
    s = trend.slope([(T0 + timedelta(days=i), 80 - 0.1 * i) for i in range(10)])
    assert s is not None
    assert round(s.kg_per_week, 3) == -0.7
    assert s.r2 == 1.0


def test_eta_for_a_steady_cut_is_a_range():
    pts = series(80.0, -0.07, 28, noise=(0.3, -0.2, 0.1, -0.3))
    e = trend.eta(pts, goal_kg=75.0, today=date(2026, 10, 28))
    assert e.on_track is True
    assert e.confidence in ("medium", "high")
    assert e.rate_kg_per_week is not None and e.rate_kg_per_week < 0
    assert e.eta_from is not None and e.eta_to is not None
    assert e.eta_from < e.eta_to


def test_eta_needs_enough_data():
    e = trend.eta(series(80, -0.1, 3), goal_kg=75, today=date(2026, 10, 4))
    assert e.confidence == "low" and e.eta_from is None
    assert "weigh-ins" in (e.reason or "")


def test_eta_when_moving_away_from_goal():
    e = trend.eta(series(70, 0.05, 21), goal_kg=65, today=date(2026, 10, 22))
    assert e.on_track is False and e.eta_from is None
    assert "away" in (e.reason or "")


def test_eta_without_goal_or_points():
    assert trend.eta([], 70, date(2026, 10, 1)).reason == "No weigh-ins yet"
    assert trend.eta(series(70, 0, 3), None, date(2026, 10, 1)).reason == "Set a target weight"
