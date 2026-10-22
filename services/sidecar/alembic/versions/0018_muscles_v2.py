"""muscles-v2: 54 detailed muscles and heads replace the 19 regions (ADR-0021)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-22

1. Keeps a copy of every exercise_muscles row in exercise_muscles_v7 (for the downgrade).
2. Re-maps free-exercise-db rows from their source muscle lists with muscle-map-v1
   (progress/muscle_map.map_detailed); every other row (ASCEND's own, calisthenics,
   activities, custom) has its hand-made v7 weights translated through the research table
   (translate_legacy: copy, not split, so readiness does not jump on migration day).
3. Renames today's and past quest metrics "sets:<region>" to the region's main muscle.
4. Recomputes every muscle_load_events row from the logged sets (doses.rebuild), so all
   history replays onto the new muscles. No set, meal, XP or quest row is deleted.

The sidecar writes a pre-migration .ascendbak before running this (main.py), so the
previous database can also be restored from Settings -> Backups.
Downgrade restores the saved v7 rows (rows created after the upgrade are rolled up with
to_legacy), renames quest metrics back and recomputes the doses.
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.intelligence import doses
from app.modules.progress.muscle_map import LEGACY_TO_V2, to_legacy, translate_legacy
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from app.modules.workouts.library import fedb_entry, load_fedb

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The muscle a v7 quest metric "sets:<region>" now counts (the table's first weight-1.0 key).
MAIN_CHILD = {old: next(k for k, w in new.items() if w >= 1.0) for old, new in LEGACY_TO_V2.items()}


def _weights(conn: sa.Connection) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    for ex_id, muscle, w in conn.execute(
        sa.text("SELECT exercise_id, muscle, weight FROM exercise_muscles")
    ):
        out.setdefault(ex_id, {})[muscle] = w
    return out


def _write(conn: sa.Connection, ex_id: int, weights: dict[str, float]) -> None:
    conn.execute(sa.text("DELETE FROM exercise_muscles WHERE exercise_id = :e"), {"e": ex_id})
    if weights:
        conn.execute(
            sa.text(
                "INSERT INTO exercise_muscles (exercise_id, muscle, weight) VALUES (:e, :m, :w)"
            ),
            [{"e": ex_id, "m": m, "w": w} for m, w in sorted(weights.items())],
        )


def _rename_quests(conn: sa.Connection, mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        conn.execute(
            sa.text("UPDATE quest_items SET metric = :n WHERE metric = :o"),
            {"n": f"sets:{new}", "o": f"sets:{old}"},
        )


def upgrade() -> None:
    conn = op.get_bind()
    op.create_table(
        "exercise_muscles_v7",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("muscle", sa.String(32), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
    )
    conn.execute(
        sa.text(
            "INSERT INTO exercise_muscles_v7 (exercise_id, muscle, weight) "
            "SELECT exercise_id, muscle, weight FROM exercise_muscles"
        )
    )
    fedb = {str(raw["id"]): raw for raw in load_fedb()["exercises"]}
    current = _weights(conn)
    rows = conn.execute(
        sa.text("SELECT id, source, source_ref, is_custom, field_sources FROM exercises")
    ).all()
    for ex_id, source, ref, is_custom, sources_raw in rows:
        sources = json.loads(sources_raw or "{}")
        old = current.get(ex_id, {})
        raw = fedb.get(ref or "")
        from_library = sources.get("muscles") in ("library", "rules")
        if source == "free-exercise-db" and raw is not None and not is_custom and from_library:
            new = fedb_entry(raw).muscles
            sources["muscle_map"] = "remapped"
        else:
            new = translate_legacy(old)
            sources["muscle_map"] = "translated"
        if not old and not new:
            continue
        _write(conn, ex_id, new)
        conn.execute(
            sa.text("UPDATE exercises SET field_sources = :s WHERE id = :i"),
            {"s": json.dumps(sources, sort_keys=True), "i": ex_id},
        )
    _rename_quests(conn, MAIN_CHILD)
    doses.rebuild(conn)


def downgrade() -> None:
    conn = op.get_bind()
    saved: dict[int, dict[str, float]] = {}
    for ex_id, muscle, w in conn.execute(
        sa.text("SELECT exercise_id, muscle, weight FROM exercise_muscles_v7")
    ):
        saved.setdefault(ex_id, {})[muscle] = w
    current = _weights(conn)
    for ex_id in sorted(set(current) | set(saved)):
        _write(conn, ex_id, saved.get(ex_id) or to_legacy(current.get(ex_id, {})))
    rows = conn.execute(sa.text("SELECT id, field_sources FROM exercises")).all()
    for ex_id, sources_raw in rows:
        sources = json.loads(sources_raw or "{}")
        if sources.pop("muscle_map", None) is not None:
            conn.execute(
                sa.text("UPDATE exercises SET field_sources = :s WHERE id = :i"),
                {"s": json.dumps(sources, sort_keys=True), "i": ex_id},
            )
    metrics = [r[0] for r in conn.execute(sa.text("SELECT DISTINCT metric FROM quest_items"))]
    back = {
        m[5:]: MUSCLE_BY_KEY[m[5:]].legacy
        for m in metrics
        if m.startswith("sets:") and m[5:] in MUSCLE_BY_KEY and MUSCLE_BY_KEY[m[5:]].legacy
    }
    _rename_quests(conn, back)
    op.drop_table("exercise_muscles_v7")
    doses.rebuild(conn)
