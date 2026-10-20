"""Per-muscle doses stored when a set is logged (the muscle_load_events table).

Since recovery-v2 the stored dose is the recovery-v2 effective set (recovery.py): the
muscle weight x intensity from RIR x volume. Storing it at log time keeps every reader
(the map, the drill-down, the activity card, quests, the coach) on the same number, and a
year of history stays a single indexed read. The RIR estimate for a set without RPE uses
the best e1RM logged BEFORE that set, so the dose depends only on what was known then.

`rebuild` recomputes every row, oldest first. Migration 0014 runs it once for data logged
before recovery-v2, and its downgrade restores the load-v1 rows.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import Connection, text

from app.modules.intelligence import recovery as rec
from app.modules.progress import muscle_load

TIME_BASED_SECTIONS = ("cardio", "martial_arts", "flexibility", "meditation")


def kind_for(measure: str | None, section: str | None, duration_s: int | None) -> rec.Kind:
    if duration_s and section in TIME_BASED_SECTIONS:
        return "time"
    if measure == "hold":
        return "hold"
    if measure == "time" and duration_s:
        return "time"
    return "reps"


def set_dose(
    *,
    muscles: Mapping[str, float],
    at: datetime,
    measure: str | None,
    section: str | None,
    reps: int,
    weight_kg: float,
    rpe: float | None,
    duration_s: int | None,
    e1rm_ref: float | None,
) -> list[tuple[str, float]]:
    """(muscle, ES) pairs for one set; empty when the set carries no load."""
    s = rec.SetInput(
        at=at,
        muscles=muscles,
        kind=kind_for(measure, section, duration_s),
        reps=reps,
        weight_kg=weight_kg,
        rpe=rpe,
        duration_s=duration_s,
        e1rm_ref=e1rm_ref,
    )
    return [(c.muscle, c.es) for c in rec.contributions([s])]


def load_v1_dose(
    muscles: Mapping[str, float], section: str | None, rpe: float | None, duration_s: int | None
) -> tuple[list[tuple[str, float]], str]:
    """The pre-v2 rows (for the migration's downgrade)."""
    if duration_s and section in TIME_BASED_SECTIONS:
        base = muscle_load.time_effective_sets(duration_s, rpe)
        version = muscle_load.TIME_FORMULA_VERSION
    else:
        base = muscle_load.effort(rpe)
        version = muscle_load.FORMULA_VERSION
    return [(m, round(w * base, 3)) for m, w in muscles.items() if w * base > 0], version


def rebuild(conn: Connection, version: str = rec.ALGO_VERSION) -> int:
    """Recompute every muscle_load_events row from the logged sets. Returns rows written."""
    weights: dict[int, dict[str, float]] = {}
    for ex_id, muscle, w in conn.execute(
        text("SELECT exercise_id, muscle, weight FROM exercise_muscles")
    ):
        weights.setdefault(ex_id, {})[muscle] = w
    rows = conn.execute(
        text(
            "SELECT s.id, s.exercise_id, s.weight_kg, s.reps, s.rpe, s.duration_s, s.e1rm, "
            "s.performed_at, e.measure, e.section FROM workout_sets s "
            "JOIN exercises e ON e.id = s.exercise_id ORDER BY s.performed_at, s.id"
        )
    ).all()
    conn.execute(text("DELETE FROM muscle_load_events"))
    best: dict[int, float] = {}
    out: list[dict[str, object]] = []
    for sid, ex_id, kg, reps, rpe, dur, e1rm, at, measure, section in rows:
        when = at if isinstance(at, datetime) else datetime.fromisoformat(str(at))
        muscles = weights.get(ex_id, {})
        if version == rec.ALGO_VERSION:
            pairs = set_dose(
                muscles=muscles,
                at=when,
                measure=measure,
                section=section,
                reps=reps or 0,
                weight_kg=kg or 0.0,
                rpe=rpe,
                duration_s=dur,
                e1rm_ref=best.get(ex_id),
            )
            v = version
        else:
            pairs, v = load_v1_dose(muscles, section, rpe, dur)
        stamp = when.strftime("%Y-%m-%d %H:%M:%S.%f")  # SQLAlchemy's SQLite format
        for muscle, es in pairs:
            out.append({"set_id": sid, "muscle": muscle, "es": es, "at": stamp, "v": v})
        if e1rm is not None and e1rm > best.get(ex_id, 0.0):
            best[ex_id] = e1rm
    if out:
        conn.execute(
            text(
                "INSERT INTO muscle_load_events (set_id, muscle, es, at, formula_version) "
                "VALUES (:set_id, :muscle, :es, :at, :v)"
            ),
            out,
        )
    return len(out)
