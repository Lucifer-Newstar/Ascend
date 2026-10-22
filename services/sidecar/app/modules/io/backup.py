"""`.ascendbak` backups (ADR-0010): a zip with a consistent SQLite snapshot and a manifest.

    ascend-20261020-091500.ascendbak
    ├── manifest.json   {"format": "ascendbak", "format_version": 1, "app_version", "schema",
    │                    "created_at", "files": {"ascend.db": {"sha256", "size"}}}
    └── ascend.db       SQLite online-backup copy (safe while the app is running)

Backups live in `<data dir>/backups/`. Restore checks the manifest, every checksum and the
schema revision (a backup from a newer app is refused), then copies the snapshot over the
live database with SQLite's backup API and migrates it to this build's head.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from app import __version__
from app.core.migrate import head_revision, run_migrations

FORMAT = "ascendbak"
FORMAT_VERSION = 1
SUFFIX = ".ascendbak"
DB_NAME = "ascend.db"
KEEP_AUTOMATIC = 5
KEEP_DAILY = 14  # one automatic snapshot per day while the app runs, two weeks kept


class BackupError(ValueError):
    """A backup could not be read or restored (message is safe to show)."""


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    size_bytes: int
    sha256: str
    created_at: datetime
    schema: str
    app_version: str
    reason: str


def backups_dir(data_dir: Path) -> Path:
    path = data_dir / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sqlite_path(engine: Engine) -> Path:
    db = engine.url.database
    if engine.dialect.name != "sqlite" or not db or db == ":memory:":
        raise BackupError("backups need the on-disk SQLite database")
    return Path(db)


def _schema_of(db_file: Path) -> str:
    con = sqlite3.connect(db_file)
    try:
        row = con.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.DatabaseError:
        row = None
    finally:
        con.close()
    return str(row[0]) if row else "none"


def create_backup(
    db_file: Path, out_dir: Path, now: datetime, reason: str = "manual"
) -> BackupInfo:
    """Snapshot `db_file` into a new .ascendbak in `out_dir` and return its details."""
    if not db_file.exists():
        raise BackupError("there is no database to back up yet")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    suffix = "" if reason == "manual" else f"-{reason}"
    target = out_dir / f"ascend-{stamp}{suffix}{SUFFIX}"
    n = 1
    while target.exists():  # two backups in the same second
        n += 1
        target = out_dir / f"ascend-{stamp}{suffix}-{n}{SUFFIX}"
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / DB_NAME
        src, dst = sqlite3.connect(db_file), sqlite3.connect(snap)
        try:
            src.backup(dst)  # consistent even while the app writes (WAL mode)
        finally:
            dst.close()
            src.close()
        manifest = {
            "format": FORMAT,
            "format_version": FORMAT_VERSION,
            "app_version": __version__,
            "schema": _schema_of(snap),
            "created_at": now.isoformat(),
            "reason": reason,
            "files": {DB_NAME: {"sha256": _sha256(snap), "size": snap.stat().st_size}},
        }
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
            z.write(snap, DB_NAME)
    return read_info(target)


def _manifest(z: zipfile.ZipFile) -> dict[str, object]:
    try:
        data = json.loads(z.read("manifest.json"))
    except (KeyError, json.JSONDecodeError) as err:
        raise BackupError("the backup has no readable manifest") from err
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise BackupError("this is not an ASCEND backup")
    if int(data.get("format_version", 0)) > FORMAT_VERSION:
        raise BackupError("this backup was made by a newer version of ASCEND")
    return data


def read_info(path: Path) -> BackupInfo:
    try:
        with zipfile.ZipFile(path) as z:
            m = _manifest(z)
    except zipfile.BadZipFile as err:
        raise BackupError("the backup file is damaged (not a valid zip)") from err
    return BackupInfo(
        path=path,
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
        created_at=datetime.fromisoformat(str(m["created_at"])),
        schema=str(m.get("schema", "none")),
        app_version=str(m.get("app_version", "")),
        reason=str(m.get("reason", "manual")),
    )


def list_backups(out_dir: Path) -> list[BackupInfo]:
    """Readable backups in the folder, newest first; damaged files are skipped."""
    infos = []
    for path in out_dir.glob(f"*{SUFFIX}"):
        try:
            infos.append(read_info(path))
        except BackupError:
            continue
    return sorted(infos, key=lambda i: (i.created_at, i.path.name), reverse=True)


def prune_automatic(out_dir: Path, keep: int = KEEP_AUTOMATIC) -> int:
    """Delete the oldest safety backups (pre-migration, pre-restore) beyond `keep`.
    Manual backups are never touched; daily ones have their own rotation (prune_daily)."""
    auto = [i for i in list_backups(out_dir) if i.reason not in ("manual", "daily")]
    removed = 0
    for info in auto[keep:]:
        info.path.unlink(missing_ok=True)
        removed += 1
    return removed


def _schema_order(rev: str) -> int:
    return int(rev) if rev.isdigit() else -1


def restore_backup(path: Path, db_file: Path, db_url: str) -> BackupInfo:
    """Validate `path` and copy its snapshot over `db_file`, then migrate to head."""
    if not path.exists():
        raise BackupError("that backup file does not exist")
    info = read_info(path)
    head = head_revision()
    if _schema_order(info.schema) > _schema_order(head):
        raise BackupError(
            f"this backup has database schema {info.schema}, newer than this app ({head}); "
            "update ASCEND first"
        )
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(path) as z:
        m = _manifest(z)
        files = m.get("files")
        if not isinstance(files, dict) or DB_NAME not in files:
            raise BackupError("the backup does not contain a database")
        z.extract(DB_NAME, tmp)
        snap = Path(tmp) / DB_NAME
        expected = files[DB_NAME].get("sha256") if isinstance(files[DB_NAME], dict) else None
        if _sha256(snap) != expected:
            raise BackupError("the backup failed its checksum; it may be damaged")
        src, dst = sqlite3.connect(snap), sqlite3.connect(db_file)
        try:
            src.backup(dst)  # replaces every page of the live database in one step
        finally:
            dst.close()
            src.close()
    run_migrations(db_url)
    return info


def backup_if_behind(db_file: Path, out_dir: Path, now: datetime) -> BackupInfo | None:
    """Before migrating an existing database to a newer schema, keep a copy of it.

    Called at start-up. Returns None for a fresh install (nothing to protect) and for a
    database already at head. Old automatic backups beyond KEEP_AUTOMATIC are pruned.
    """
    if not db_file.exists() or db_file.stat().st_size == 0:
        return None
    current = _schema_of(db_file)
    if current in ("none", head_revision()):
        return None
    info = create_backup(db_file, out_dir, now, reason="pre-migration")
    prune_automatic(out_dir)
    return info


def prune_daily(out_dir: Path, keep: int = KEEP_DAILY) -> int:
    """Keep the newest `keep` daily snapshots and delete older ones."""
    daily = [i for i in list_backups(out_dir) if i.reason == "daily"]
    for info in daily[keep:]:
        info.path.unlink(missing_ok=True)
    return max(0, len(daily) - keep)


def backup_daily_if_due(db_file: Path, out_dir: Path, now: datetime) -> BackupInfo | None:
    """Write today's automatic snapshot unless one exists for `now`'s date, then rotate.

    Called when the sidecar starts and about hourly while it runs (main.lifespan), so a
    PC that is only on for an evening still gets that day's copy. Returns None when
    today's snapshot already exists or there is no database yet.
    """
    if not db_file.exists() or db_file.stat().st_size == 0:
        return None
    today = now.date()
    if any(i.reason == "daily" and i.created_at.date() == today for i in list_backups(out_dir)):
        return None
    info = create_backup(db_file, out_dir, now, reason="daily")
    prune_daily(out_dir)
    return info
