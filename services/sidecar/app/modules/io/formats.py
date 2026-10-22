"""Parsers for workout exports from other apps.

Every parser turns a CSV file into the same flat `ImportedSet` rows, so the
service never needs to know which app a row came from. Supported formats:

* ``strong_csv``       Strong's classic export: semicolon or comma separated, with a
                       "Weight Unit" column (kg / lbs) and "Distance Unit".
* ``strong_csv_2025``  Strong's newer export: comma separated, no unit columns (the
                       weights are in the unit the user chose in Strong), a "Duration"
                       column like "1h 5m" and RPE as the last column.
* ``hevy_csv``         Hevy: quoted, snake_case headers, weight_kg or weight_lbs,
                       start/end time like "18 Oct 2026, 18:02".

Warm-up sets are parsed (``warmup=True``) so the report can count them; the
service skips them by default.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Format = Literal["strong_csv", "strong_csv_2025", "hevy_csv"]
Unit = Literal["kg", "lb"]

LB_TO_KG = 0.45359237
MILE_TO_M = 1609.344


class ImportFormatError(ValueError):
    """The file is not a CSV this parser understands (message is safe to show)."""


@dataclass(frozen=True)
class ImportedSet:
    workout_title: str
    started_at: datetime
    exercise: str
    set_index: int
    weight_kg: float
    reps: int
    rpe: float | None = None
    duration_s: int | None = None
    distance_m: float | None = None
    warmup: bool = False
    workout_minutes: float | None = None
    finished_at: datetime | None = None


STRONG_CLASSIC = {"date", "workout name", "exercise name", "set order", "weight", "weight unit"}
STRONG_2025 = {"date", "workout name", "duration", "exercise name", "set order", "weight"}
HEVY = {"title", "start_time", "exercise_title", "set_index", "set_type"}


def _sniff(text: str) -> tuple[list[str], str]:
    """Lower-cased header row and the delimiter (Strong's classic export uses ';')."""
    first = text.lstrip("\ufeff").splitlines()[0] if text.strip() else ""
    delimiter = ";" if first.count(";") > first.count(",") else ","
    reader = csv.reader(io.StringIO(first), delimiter=delimiter)
    header = [h.strip().lower() for h in next(reader, [])]
    return header, delimiter


def detect_format(text: str) -> Format:
    """Which app wrote this CSV, from its header row alone."""
    header, _ = _sniff(text)
    cols = set(header)
    if HEVY <= cols:
        return "hevy_csv"
    if STRONG_CLASSIC <= cols:
        return "strong_csv"
    if STRONG_2025 <= cols:
        return "strong_csv_2025"
    raise ImportFormatError(
        "this does not look like a Strong or Hevy export (the header row was not recognised)"
    )


def _rows(text: str) -> list[dict[str, str]]:
    header, delimiter = _sniff(text)
    reader = csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=delimiter)
    next(reader, None)
    out = []
    for raw in reader:
        if not any(cell.strip() for cell in raw):
            continue
        out.append(
            {header[i]: _undefuse(cell.strip()) for i, cell in enumerate(raw) if i < len(header)}
        )
    return out


def _undefuse(cell: str) -> str:
    """Drop the "'" a spreadsheet-safe export puts before a leading = + - @ (ASCEND's own
    CSV export does this; see progress.history.csv_text)."""
    if len(cell) > 1 and cell[0] == "'" and cell[1] in "=+-@":
        return cell[1:]
    return cell


def _num(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    n = _num(value)
    return int(round(n)) if n is not None else None


_DURATION = re.compile(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?\s*(?:(\d+)\s*s)?", re.I)


def parse_duration_minutes(value: str | None) -> float | None:
    """Strong's "1h 5m", "45m", "50s" or plain seconds -> minutes."""
    if not value:
        return None
    if value.isdigit():
        return int(value) / 60
    m = _DURATION.fullmatch(value.strip())
    if not m or not any(m.groups()):
        return None
    h, mins, s = (int(g) if g else 0 for g in m.groups())
    return h * 60 + mins + s / 60


def _strong_date(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ImportFormatError(f"unrecognised date {value!r}")


def _hevy_date(value: str) -> datetime:
    for fmt in ("%d %b %Y, %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ImportFormatError(f"unrecognised date {value!r}")


def _set_order(value: str) -> tuple[int, bool]:
    """Strong writes 1, 2, 3 for working sets and W (warm-up) / D (drop) / F (failure)."""
    if value.isdigit():
        return int(value), False
    return 0, value.strip().upper() == "W"


def parse_strong(text: str, unit: Unit = "kg") -> list[ImportedSet]:
    """Both Strong layouts. `unit` applies to the 2025 layout, which has no unit column."""
    fmt = detect_format(text)
    if fmt == "hevy_csv":
        raise ImportFormatError("this is a Hevy export; import it as Hevy")
    out: list[ImportedSet] = []
    for row in _rows(text):
        started = _strong_date(row.get("date", ""))
        if fmt == "strong_csv":
            row_unit = "lb" if row.get("weight unit", "kg").lower().startswith("lb") else "kg"
            minutes = parse_duration_minutes(row.get("workout duration"))
            dist_unit = row.get("distance unit", "").lower()
        else:
            row_unit = unit
            minutes = parse_duration_minutes(row.get("duration"))
            dist_unit = "km"
        index, warmup = _set_order(row.get("set order", ""))
        weight = _num(row.get("weight")) or 0.0
        distance = _num(row.get("distance"))
        if distance is not None:
            distance = distance * (MILE_TO_M if dist_unit.startswith("mi") else 1000.0)
        seconds = _int(row.get("seconds"))
        out.append(
            ImportedSet(
                workout_title=row.get("workout name", "") or "Workout",
                started_at=started,
                exercise=row.get("exercise name", ""),
                set_index=index,
                weight_kg=round(weight * (LB_TO_KG if row_unit == "lb" else 1.0), 2),
                reps=_int(row.get("reps")) or 0,
                rpe=_num(row.get("rpe")),
                duration_s=seconds or None,
                distance_m=distance or None,
                warmup=warmup,
                workout_minutes=minutes,
                finished_at=started + timedelta(minutes=minutes) if minutes else None,
            )
        )
    return out


def parse_hevy(text: str) -> list[ImportedSet]:
    if detect_format(text) != "hevy_csv":
        raise ImportFormatError("this is not a Hevy export")
    out: list[ImportedSet] = []
    for row in _rows(text):
        started = _hevy_date(row.get("start_time", ""))
        end = row.get("end_time")
        finished = _hevy_date(end) if end else None
        if "weight_kg" in row:
            weight = _num(row.get("weight_kg")) or 0.0
        else:
            weight = (_num(row.get("weight_lbs")) or 0.0) * LB_TO_KG
        if "distance_km" in row:
            km = _num(row.get("distance_km"))
            distance = km * 1000 if km is not None else None
        else:
            miles = _num(row.get("distance_miles"))
            distance = miles * MILE_TO_M if miles is not None else None
        index = (_int(row.get("set_index")) or 0) + 1  # Hevy counts from 0
        minutes = (finished - started).total_seconds() / 60 if finished else None
        out.append(
            ImportedSet(
                workout_title=row.get("title", "") or "Workout",
                started_at=started,
                exercise=row.get("exercise_title", ""),
                set_index=index,
                weight_kg=round(weight, 2),
                reps=_int(row.get("reps")) or 0,
                rpe=_num(row.get("rpe")),
                duration_s=_int(row.get("duration_seconds")) or None,
                distance_m=distance or None,
                warmup=row.get("set_type", "normal").lower() == "warmup",
                workout_minutes=minutes,
                finished_at=finished,
            )
        )
    return out
