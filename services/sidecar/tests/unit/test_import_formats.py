from datetime import datetime
from pathlib import Path

import pytest

from app.modules.io.formats import (
    ImportFormatError,
    detect_format,
    parse_duration_minutes,
    parse_hevy,
    parse_strong,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "import"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "fmt"),
    [
        ("strong_classic.csv", "strong_csv"),
        ("strong_2025.csv", "strong_csv_2025"),
        ("hevy.csv", "hevy_csv"),
    ],
)
def test_detects_each_format_from_the_header(name, fmt):
    assert detect_format(read(name)) == fmt


def test_rejects_an_unknown_csv_with_a_readable_message():
    with pytest.raises(ImportFormatError, match="Strong or Hevy"):
        detect_format("name,calories\nrice,200\n")


def test_a_byte_order_mark_does_not_hide_the_header():
    assert detect_format("\ufeff" + read("strong_2025.csv")) == "strong_csv_2025"


def test_strong_classic_converts_pounds_and_miles_and_flags_warmups():
    rows = parse_strong(read("strong_classic.csv"))
    assert len(rows) == 8
    warm = rows[0]
    assert warm.warmup is True and warm.set_index == 0
    squat = next(r for r in rows if r.exercise == "Squat (Barbell)")
    assert squat.weight_kg == pytest.approx(102.06, abs=0.01)  # 225 lb
    assert squat.rpe == 8.5
    run = next(r for r in rows if r.exercise == "Running")
    assert run.distance_m == pytest.approx(5150, abs=1)  # 3.2 mi
    assert run.duration_s == 1500
    bench = rows[1]
    assert bench.started_at == datetime(2026, 9, 1, 18, 2, 11)
    assert bench.workout_minutes == 65
    assert bench.finished_at == datetime(2026, 9, 1, 19, 7, 11)


def test_strong_2025_uses_the_unit_the_user_picks():
    kg = parse_strong(read("strong_2025.csv"))
    lb = parse_strong(read("strong_2025.csv"), unit="lb")
    pulldown_kg = next(r for r in kg if r.exercise.startswith("Lat"))
    pulldown_lb = next(r for r in lb if r.exercise.startswith("Lat"))
    assert pulldown_kg.weight_kg == 135
    assert pulldown_lb.weight_kg == pytest.approx(61.23, abs=0.01)
    assert pulldown_kg.rpe == 8
    assert pulldown_kg.workout_minutes == 70


def test_hevy_counts_sets_from_one_and_reads_cardio():
    rows = parse_hevy(read("hevy.csv"))
    assert [r.set_index for r in rows[:2]] == [1, 2]
    assert rows[0].warmup is True and rows[1].warmup is False
    assert rows[1].weight_kg == 70 and rows[1].rpe == 8.5
    tread = rows[-1]
    assert tread.distance_m == pytest.approx(5100)
    assert tread.duration_s == 1800
    assert tread.workout_minutes == 35


def test_parsers_refuse_the_other_apps_file():
    with pytest.raises(ImportFormatError, match="Hevy"):
        parse_strong(read("hevy.csv"))
    with pytest.raises(ImportFormatError):
        parse_hevy(read("strong_2025.csv"))


@pytest.mark.parametrize(
    ("text", "minutes"),
    [("1h 5m", 65), ("45m", 45), ("2h", 120), ("90", 1.5), ("", None), ("soon", None)],
)
def test_parse_duration(text, minutes):
    assert parse_duration_minutes(text) == minutes
