from dataclasses import dataclass
from datetime import date, datetime

from app.core.events import Event, EventBus, SetLogged, WorkoutLogged


def test_payload_serialises_dates_as_iso_strings():
    ev = WorkoutLogged(workout_id=3, day=date(2026, 10, 20), hard_sets=5, active_minutes=41.5)
    assert ev.payload() == {
        "workout_id": 3,
        "day": "2026-10-20",
        "hard_sets": 5,
        "active_minutes": 41.5,
    }
    assert ev.event_name() == "WorkoutLogged"
    assert ev.VERSION == 1


def test_bus_dispatches_only_to_matching_type_in_subscription_order():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(SetLogged, lambda _s, e: seen.append(f"a{e.set_id}"))
    bus.subscribe(SetLogged, lambda _s, e: seen.append(f"b{e.set_id}"))
    bus.subscribe(WorkoutLogged, lambda _s, _e: seen.append("workout"))
    ev = SetLogged(
        set_id=7,
        workout_id=1,
        exercise_id=2,
        weight_kg=60,
        reps=8,
        rpe=8,
        performed_at=datetime(2026, 10, 20, 9),
        is_pr=False,
    )
    bus.publish(None, ev)  # type: ignore[arg-type]
    assert seen == ["a7", "b7"]
    assert bus.handler_count(WorkoutLogged) == 1


def test_version_can_be_overridden_per_event():
    @dataclass(frozen=True)
    class Renamed(Event):
        VERSION = 2
        value: int

    assert Renamed(value=1).VERSION == 2
    assert Renamed(value=1).payload() == {"value": 1}
