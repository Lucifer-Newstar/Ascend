"""Security review M1: one odd file in the backups folder must not break the list or
stop the automatic daily backups."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from app import main as app_main
from app.main import daily_backup_once
from app.modules.io import backup


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "ascend.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE t (x INTEGER)")
    return db


def _fake(out: Path, name: str, **manifest: object) -> Path:
    path = out / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": "ascendbak", **manifest}))
        z.writestr("ascend.db", b"")
    return path


BAD_MANIFESTS = [
    pytest.param({"format_version": 1}, id="no-created_at"),
    pytest.param({"format_version": "one", "created_at": "2026-10-01T10:00:00"}, id="bad-version"),
    pytest.param({"format_version": 1, "created_at": "yesterday"}, id="bad-date"),
    pytest.param({"format_version": 1, "created_at": 12}, id="number-date"),
    pytest.param({"format_version": None, "created_at": "2026-10-01T10:00:00"}, id="null-version"),
]


@pytest.mark.parametrize("manifest", BAD_MANIFESTS)
def test_read_info_turns_a_bad_manifest_into_backup_error(tmp_path: Path, manifest) -> None:
    with pytest.raises(backup.BackupError):
        backup.read_info(_fake(tmp_path, "x.ascendbak", **manifest))


@pytest.mark.parametrize("manifest", BAD_MANIFESTS)
def test_list_skips_a_bad_manifest(tmp_path: Path, manifest) -> None:
    db = _db(tmp_path)
    out = tmp_path / "backups"
    out.mkdir()
    good = backup.create_backup(db, out, datetime(2026, 10, 1, 9, 0), reason="manual")
    _fake(out, "bad.ascendbak", **manifest)
    assert [i.path for i in backup.list_backups(out)] == [good.path]


def test_naive_and_aware_dates_sort_together(tmp_path: Path) -> None:
    out = tmp_path / "backups"
    out.mkdir()
    _fake(out, "a.ascendbak", format_version=1, created_at="2026-10-01T10:00:00")
    _fake(out, "b.ascendbak", format_version=1, created_at="2026-10-02T10:00:00+05:30")
    names = [i.path.name for i in backup.list_backups(out)]
    assert names == ["b.ascendbak", "a.ascendbak"]
    assert all(i.created_at.tzinfo is None for i in backup.list_backups(out))


def test_backups_endpoint_survives_a_bad_file(client, settings) -> None:
    out = settings.data_dir / "backups"
    out.mkdir(parents=True, exist_ok=True)
    _fake(out, "bad.ascendbak", format_version="x", created_at="2026-10-01T10:00:00")
    r = client.get("/backups")
    assert r.status_code == 200 and r.json() == []


def test_daily_backup_still_runs_next_to_a_bad_file(tmp_path: Path) -> None:
    db = _db(tmp_path)
    out = tmp_path / "backups"
    out.mkdir()
    _fake(out, "bad.ascendbak", format_version=1)  # no created_at
    info = backup.backup_daily_if_due(db, out, datetime(2026, 10, 22, 9, 0))
    assert info is not None and info.reason == "daily"


class _App:
    class state:  # noqa: N801 - mimics FastAPI's app.state
        pass


def test_daily_backup_once_never_raises(monkeypatch, caplog) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(backup, "sqlite_path", boom)
    with caplog.at_level(logging.WARNING, logger="ascend"):
        daily_backup_once(_App())  # type: ignore[arg-type]
    assert "daily backup failed" in caplog.text


def test_daily_loop_keeps_going_after_an_error(monkeypatch, caplog) -> None:
    calls: list[int] = []

    def flaky(_app) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("unexpected")

    monkeypatch.setattr(app_main, "daily_backup_once", flaky)
    monkeypatch.setattr(app_main, "DAILY_BACKUP_CHECK_S", 0.01)

    async def run() -> None:
        task = asyncio.create_task(app_main._daily_backups(_App()))  # type: ignore[arg-type]
        while len(calls) < 3:
            await asyncio.sleep(0.01)
        task.cancel()

    with caplog.at_level(logging.ERROR, logger="ascend"):
        asyncio.run(asyncio.wait_for(run(), timeout=5))
    assert len(calls) >= 3
    assert "daily backup check crashed" in caplog.text
