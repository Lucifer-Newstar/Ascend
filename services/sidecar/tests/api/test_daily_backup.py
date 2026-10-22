"""Daily automatic snapshots: one per calendar day, 14 kept, safety and manual backups untouched."""

from datetime import datetime, timedelta
from pathlib import Path

from app.main import daily_backup_once
from app.modules.io import backup


def _db(tmp_path: Path) -> Path:
    import sqlite3

    db = tmp_path / "ascend.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE t (x INTEGER)")
        c.execute("INSERT INTO t VALUES (1)")
    return db


def test_one_snapshot_per_day(tmp_path: Path) -> None:
    db, out = _db(tmp_path), tmp_path / "backups"
    out.mkdir()
    first = backup.backup_daily_if_due(db, out, datetime(2026, 10, 22, 9, 0))
    assert first is not None and first.reason == "daily"
    assert backup.backup_daily_if_due(db, out, datetime(2026, 10, 22, 21, 30)) is None
    assert backup.backup_daily_if_due(db, out, datetime(2026, 10, 23, 0, 5)) is not None
    assert [i.reason for i in backup.list_backups(out)] == ["daily", "daily"]


def test_rotation_keeps_the_newest_14_and_leaves_other_backups(tmp_path: Path) -> None:
    db, out = _db(tmp_path), tmp_path / "backups"
    out.mkdir()
    start = datetime(2026, 10, 1, 8, 0)
    manual = backup.create_backup(db, out, start, reason="manual")
    safety = backup.create_backup(db, out, start, reason="pre-migration")
    for d in range(20):
        backup.backup_daily_if_due(db, out, start + timedelta(days=d))
    infos = backup.list_backups(out)
    daily = [i for i in infos if i.reason == "daily"]
    assert len(daily) == backup.KEEP_DAILY == 14
    assert min(i.created_at for i in daily).date() == (start + timedelta(days=6)).date()
    assert manual.path.exists() and safety.path.exists()
    # Safety-backup pruning does not count or delete daily snapshots.
    assert backup.prune_automatic(out, keep=5) == 0
    assert len([i for i in backup.list_backups(out) if i.reason == "daily"]) == 14


def test_no_database_no_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "backups"
    out.mkdir()
    assert backup.backup_daily_if_due(tmp_path / "missing.db", out, datetime(2026, 10, 22)) is None


def test_the_app_hook_writes_todays_snapshot_and_a_restore_brings_data_back(
    client, settings, clock, profile
) -> None:
    daily_backup_once(client.app)
    snaps = [b for b in client.get("/backups").json() if b["reason"] == "daily"]
    assert len(snaps) == 1 and snaps[0]["size_bytes"] > 0
    daily_backup_once(client.app)  # same day: nothing new
    assert len([b for b in client.get("/backups").json() if b["reason"] == "daily"]) == 1

    client.put("/profile", json={**profile, "name": "Changed"})
    r = client.post("/restore", json={"path": snaps[0]["path"]})
    assert r.status_code == 200
    assert client.get("/profile").json()["name"] == "Navin"
