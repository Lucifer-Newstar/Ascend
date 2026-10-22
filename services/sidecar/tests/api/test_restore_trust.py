"""Security review M2: restore only trusts files in the backups folder, and checks the
database inside before it replaces the live one."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.modules.io import backup


def _backup(client) -> Path:
    r = client.post("/backup")
    assert r.status_code == 201
    return Path(r.json()["path"])


def _repack(src: Path, name: str, edit) -> Path:
    """Copy a backup, run `edit(sqlite3.Connection)` on its database and fix the manifest
    checksum, so only the new checks can catch it (the checksum is not a signature)."""
    work = src.parent / "work.db"
    with zipfile.ZipFile(src) as z:
        work.write_bytes(z.read("ascend.db"))
        manifest = json.loads(z.read("manifest.json"))
    c = sqlite3.connect(work)
    try:
        with c:
            edit(c)
    finally:
        c.close()  # checkpoints the WAL into the file we read next
    data = work.read_bytes()
    work.unlink()
    manifest["files"]["ascend.db"] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    out = src.with_name(name)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr("ascend.db", data)
    return out


def _restore(client, path: str):
    return client.post("/restore", json={"path": path})


def _nothing_changed(client) -> None:
    assert client.get("/profile").json()["name"] == "Navin"
    assert all(b["reason"] != "pre-restore" for b in client.get("/backups").json())


def test_a_backup_outside_the_backups_folder_is_refused(client, settings, profile) -> None:
    outside = settings.data_dir / "copied.ascendbak"
    shutil.copy(_backup(client), outside)
    r = _restore(client, str(outside))
    assert r.status_code == 422 and "backups folder" in r.json()["detail"]
    _nothing_changed(client)


@pytest.mark.parametrize(
    "path",
    [
        r"\\attacker.example\share\x.ascendbak",
        "//attacker.example/share/x.ascendbak",
        r"\\?\UNC\attacker.example\share\x.ascendbak",
    ],
)
def test_network_paths_are_refused_without_touching_them(
    client, profile, monkeypatch, path
) -> None:
    touched: list[str] = []
    monkeypatch.setattr(Path, "exists", lambda self: touched.append(str(self)) or False)
    r = _restore(client, path)
    assert r.status_code == 422 and "network" in r.json()["detail"]
    assert touched == []


def test_a_symlink_in_the_backups_folder_to_elsewhere_is_refused(client, settings, profile) -> None:
    real = settings.data_dir / "elsewhere.ascendbak"
    shutil.copy(_backup(client), real)
    link = settings.data_dir / "backups" / "link.ascendbak"
    link.symlink_to(real)
    r = _restore(client, str(link))
    assert r.status_code == 422 and "backups folder" in r.json()["detail"]


def test_a_bare_file_name_means_the_backups_folder(client, profile) -> None:
    path = _backup(client)
    client.put(
        "/profile",
        json={
            "name": "After",
            "age": 21,
            "sex": "male",
            "height_cm": 175,
            "weight_kg": 70,
            "goal": "bulk",
            "activity": "moderate",
        },
    )
    r = _restore(client, path.name)
    assert r.status_code == 200
    assert client.get("/profile").json()["name"] == "Navin"


@pytest.mark.parametrize(
    ("sql", "word"),
    [
        (
            "CREATE TRIGGER evil AFTER INSERT ON workouts BEGIN DELETE FROM workouts; END",
            "trigger",
        ),
        ("CREATE VIEW sneaky AS SELECT 1", "view"),
    ],
)
def test_a_database_with_triggers_or_views_is_refused(client, profile, sql, word) -> None:
    bad = _repack(_backup(client), f"{word}.ascendbak", lambda c: c.execute(sql))
    r = _restore(client, str(bad))
    assert r.status_code == 422 and word in r.json()["detail"]
    _nothing_changed(client)


def test_a_corrupt_database_with_a_matching_checksum_is_refused(client, profile) -> None:
    src = _backup(client)

    def corrupt(c: sqlite3.Connection) -> None:
        c.execute("PRAGMA writable_schema = ON")
        c.execute("UPDATE sqlite_master SET rootpage = 9999 WHERE name = 'workouts'")

    bad = _repack(src, "corrupt.ascendbak", corrupt)
    r = _restore(client, str(bad))
    assert r.status_code == 422 and "integrity" in r.json()["detail"]
    _nothing_changed(client)


def test_a_database_without_the_app_schema_is_refused(client, profile) -> None:
    def wipe(c: sqlite3.Connection) -> None:
        c.execute("DROP TABLE alembic_version")

    bad = _repack(_backup(client), "foreign.ascendbak", wipe)
    r = _restore(client, str(bad))
    assert r.status_code == 422 and "ASCEND database" in r.json()["detail"]


def test_an_oversized_database_is_refused_before_extraction(client, profile, monkeypatch) -> None:
    path = _backup(client)
    monkeypatch.setattr(backup, "MAX_DB_BYTES", 1024)
    r = _restore(client, str(path))
    assert r.status_code == 422 and "too large" in r.json()["detail"]
    _nothing_changed(client)


def test_a_lying_size_header_is_still_refused(tmp_path, monkeypatch) -> None:
    """ZipInfo.file_size comes from the file itself. zipfile stops at the claimed size and
    then fails the CRC; the copy also counts bytes, so either way nothing big lands."""
    src = tmp_path / "big.bin"
    src.write_bytes(b"\0" * 5000)
    zpath = tmp_path / "z.zip"
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(src, "ascend.db")
    monkeypatch.setattr(backup, "MAX_DB_BYTES", 1000)
    with zipfile.ZipFile(zpath) as z:
        info = z.getinfo("ascend.db")
        info.file_size = 10  # pretend it is tiny
        with pytest.raises(backup.BackupError):
            backup._extract_capped(z, info, tmp_path / "out.db")


def test_pre_restore_safety_copies_are_pruned(client, clock, profile) -> None:
    """Review L18: only pre-migration backups triggered pruning, so every restore left
    one more pre-restore copy behind forever."""
    from datetime import timedelta

    path = _backup(client)
    for _ in range(backup.KEEP_AUTOMATIC + 3):
        clock.now += timedelta(minutes=1)
        assert _restore(client, path.name).status_code == 200
    reasons = [b["reason"] for b in client.get("/backups").json()]
    assert reasons.count("pre-restore") == backup.KEEP_AUTOMATIC
    assert reasons.count("manual") == 1
