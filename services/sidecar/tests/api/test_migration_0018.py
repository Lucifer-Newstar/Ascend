"""Migration 0018 (taxonomy v2, ADR-0021): an existing user's history survives the move."""

import sqlite3

from fastapi.testclient import TestClient

from alembic import command
from app.core.config import Settings
from app.core.migrate import alembic_config
from app.main import create_app
from app.modules.io import backup
from app.modules.progress.taxonomy import LEGACY_REGIONS, MUSCLE_BY_KEY

from ..conftest import TOKEN


def _rows(settings: Settings, sql: str) -> list[tuple]:
    con = sqlite3.connect(settings.data_dir / "test.db")
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def _counts(settings: Settings) -> dict[str, int]:
    tables = ("workouts", "workout_sets", "xp_events", "quest_items", "meals")
    return {t: _rows(settings, f"SELECT COUNT(*) FROM {t}")[0][0] for t in tables}


def test_v7_history_survives_the_move_to_54_muscles(settings, clock):
    app = create_app(settings, clock=clock, outbox_interval=0)
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as c:
        squat = next(
            e["id"]
            for e in c.get("/exercises", params={"q": "Back Squat"}).json()
            if e["name"] == "Back Squat"
        )
        w = c.post("/workouts").json()["id"]
        for _ in range(3):
            c.post(
                f"/workouts/{w}/sets",
                json={"exercise_id": squat, "weight_kg": 80, "reps": 5, "rpe": 8},
            )
        c.post(f"/workouts/{w}/finish")
        c.get("/quests/today")
    # Go back to a v7 database, as an existing user has it.
    cfg = alembic_config(settings.resolved_db_url)
    command.downgrade(cfg, "0017")
    before = _counts(settings)
    v7_keys = {r[0] for r in _rows(settings, "SELECT DISTINCT muscle FROM exercise_muscles")}
    assert v7_keys <= set(LEGACY_REGIONS)
    assert before["workout_sets"] == 3

    # Opening the app again migrates it, after a pre-migration backup.
    create_app(settings, clock=clock, outbox_interval=0)
    [info] = backup.list_backups(backup.backups_dir(settings.data_dir))
    assert info.reason == "pre-migration" and info.schema == "0017"
    assert _counts(settings) == before  # no set, workout, XP event, quest item or meal lost
    keys = {r[0] for r in _rows(settings, "SELECT DISTINCT muscle FROM exercise_muscles")}
    assert keys <= set(MUSCLE_BY_KEY) and "vastus_lateralis" in keys
    loads = {r[0] for r in _rows(settings, "SELECT DISTINCT muscle FROM muscle_load_events")}
    assert {"vastus_lateralis", "vastus_medialis", "gluteus_maximus"} <= loads
    assert loads <= set(MUSCLE_BY_KEY)
    metrics = [
        r[0] for r in _rows(settings, "SELECT metric FROM quest_items WHERE metric LIKE 'sets:%'")
    ]
    assert all(m.split(":", 1)[1] in MUSCLE_BY_KEY for m in metrics)

    # And the downgrade gives the v7 rows back.
    command.downgrade(cfg, "0017")
    assert {
        r[0] for r in _rows(settings, "SELECT DISTINCT muscle FROM exercise_muscles")
    } == v7_keys
    assert _counts(settings) == before
