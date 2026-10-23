"""`.ascendbak` backups (ADR-0010): a zip with a consistent SQLite snapshot and a manifest.

    ascend-20261020-091500.ascendbak
    ├── manifest.json   {"format": "ascendbak", "format_version": 1, "app_version", "schema",
    │                    "created_at", "files": {"ascend.db": {"sha256", "size"}}}
    ├── ascend.db       SQLite online-backup copy (safe while the app is running)
    └── photos/…        progress photos (v1.1), each listed in "files" with its checksum

Backups live in `<data dir>/backups/`. Restore checks the manifest, every checksum and the
schema revision (a backup from a newer app is refused), then copies the snapshot over the
live database with SQLite's backup API and migrates it to this build's head.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
import zipfile
import zlib
from collections.abc import Callable
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
# Largest database a restore will unpack. A year of daily logging is a few MB; the cap
# only exists so a crafted zip (a "zip bomb") can't fill the disk.
MAX_DB_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_PHOTO_BYTES = 16 * 1024 * 1024
PHOTO_NAME = re.compile(r"^photos/[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9a-f]{16}\.(jpg|png)$")


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


def _photo_files(db_file: Path) -> list[Path]:
    folder = db_file.parent / "photos"
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if PHOTO_NAME.match(f"photos/{p.name}"))


def create_backup(
    db_file: Path, out_dir: Path, now: datetime, reason: str = "manual"
) -> BackupInfo:
    """Snapshot `db_file` (and the progress photos beside it) into a new .ascendbak in
    `out_dir` and return its details."""
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
        photos = _photo_files(db_file)
        files = manifest["files"]
        assert isinstance(files, dict)
        for p in photos:
            files[f"photos/{p.name}"] = {"sha256": _sha256(p), "size": p.stat().st_size}
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
            z.write(snap, DB_NAME)
            for p in photos:
                z.write(p, f"photos/{p.name}")
    return read_info(target)


def _manifest(z: zipfile.ZipFile) -> dict[str, object]:
    try:
        if z.getinfo("manifest.json").file_size > MAX_MANIFEST_BYTES:
            raise BackupError("the backup manifest is too large")
        data = json.loads(z.read("manifest.json"))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as err:
        raise BackupError("the backup has no readable manifest") from err
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise BackupError("this is not an ASCEND backup")
    try:
        version = int(data.get("format_version", 0))
    except (TypeError, ValueError) as err:
        raise BackupError("the backup manifest has an invalid format_version") from err
    if version > FORMAT_VERSION:
        raise BackupError("this backup was made by a newer version of ASCEND")
    return data


def _created_at(m: dict[str, object]) -> datetime:
    """The manifest's created_at as naive local time (the app's convention), so backups
    written with and without a UTC offset sort together."""
    raw = m.get("created_at")
    if not isinstance(raw, str):
        raise BackupError("the backup manifest has no created_at date")
    try:
        at = datetime.fromisoformat(raw)
    except ValueError as err:
        raise BackupError("the backup manifest has an invalid created_at date") from err
    return at.astimezone().replace(tzinfo=None) if at.tzinfo is not None else at


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
        created_at=_created_at(m),
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


def prune_automatic(
    out_dir: Path, keep: int = KEEP_AUTOMATIC, keep_paths: set[Path] | frozenset[Path] = frozenset()
) -> int:
    """Delete the oldest safety backups (pre-migration, pre-restore) beyond `keep`.
    Manual backups are never touched; daily ones have their own rotation (prune_daily).
    Files in `keep_paths` (the one just restored, the new safety copy) are never deleted."""
    auto = [i for i in list_backups(out_dir) if i.reason not in ("manual", "daily")]
    protected = {k.resolve() for k in keep_paths}
    removed = 0
    for info in auto[keep:]:
        if info.path.resolve() in protected:
            continue
        info.path.unlink(missing_ok=True)
        removed += 1
    return removed


def _schema_order(rev: str) -> int:
    return int(rev) if rev.isdigit() else -1


def resolve_restore_path(raw: str, folder: Path) -> Path:
    """The backup a restore request names, which must be a file in the backups folder.

    A restore replaces all of the user's data, so only files the app itself wrote (or the
    user copied into the folder) are accepted. Network paths are refused before anything
    touches them: opening \\\\host\\share\\x makes Windows sign in to that host (NTLM).
    A bare file name means a file in the backups folder.
    """
    text = raw.strip()
    if text.startswith(("\\\\", "//")):
        raise BackupError("network paths can't be restored; copy the backup to this PC first")
    path = Path(text)
    if path.suffix != SUFFIX:
        raise BackupError(f"choose a {SUFFIX} file")
    if not path.is_absolute() and path.name == text:
        path = folder / path
    try:
        resolved, home = path.resolve(), folder.resolve()
    except OSError as err:
        raise BackupError("that backup file does not exist") from err
    if resolved.parent != home:
        raise BackupError("only backups in the ASCEND backups folder can be restored")
    if not resolved.is_file():
        raise BackupError("that backup file does not exist")
    return resolved


def _extract_capped(z: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path) -> None:
    """Unpack one member, refusing more than MAX_DB_BYTES. The size in the zip header is
    the file's own claim, so the copy counts the bytes as well."""
    too_big = BackupError("the database in this backup is too large to restore")
    if info.file_size > MAX_DB_BYTES:
        raise too_big
    written = 0
    try:
        with z.open(info) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_DB_BYTES:
                    raise too_big
                dst.write(chunk)
    except (zipfile.BadZipFile, zlib.error) as err:
        raise BackupError("the backup file is damaged") from err


def check_snapshot(snap: Path) -> None:
    """Refuse a database that is damaged, isn't ASCEND's, or carries schema objects the
    app never creates. Triggers and views run inside the app's own queries later, so a
    crafted backup could use them to rewrite or delete data; ASCEND's schema has none."""
    try:
        conn = sqlite3.connect(f"file:{snap.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as err:
        raise BackupError("the database in this backup can't be opened") from err
    try:
        conn.execute("PRAGMA trusted_schema = OFF")
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        if [r[0] for r in rows] != ["ok"]:
            raise BackupError("the database in this backup failed its integrity check")
        kinds = conn.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('trigger', 'view')"
        ).fetchall()
        if kinds:
            kind, name = kinds[0]
            raise BackupError(f"the database in this backup has an unexpected {kind} ({name})")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "alembic_version" not in tables:
            raise BackupError("the file in this backup is not an ASCEND database")
    except sqlite3.DatabaseError as err:
        raise BackupError("the database in this backup failed its integrity check") from err
    finally:
        conn.close()


def restore_backup(
    path: Path, db_file: Path, db_url: str, before_replace: Callable[[], None] | None = None
) -> BackupInfo:
    """Validate `path` and copy its snapshot over `db_file`, then migrate to head.
    Callers pass a path from resolve_restore_path(). `before_replace` runs once every
    check has passed, just before the live database is overwritten (the API takes its
    pre-restore safety copy there, so a refused file leaves no stray backup)."""
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
        try:
            member = z.getinfo(DB_NAME)
        except KeyError as err:
            raise BackupError("the backup does not contain a database") from err
        snap = Path(tmp) / DB_NAME
        _extract_capped(z, member, snap)
        expected = files[DB_NAME].get("sha256") if isinstance(files[DB_NAME], dict) else None
        if _sha256(snap) != expected:
            raise BackupError("the backup failed its checksum; it may be damaged")
        # The checksum sits in the same zip, so it catches damage, not tampering.
        check_snapshot(snap)
        if before_replace is not None:
            before_replace()
        src, dst = sqlite3.connect(snap), sqlite3.connect(db_file)
        try:
            src.backup(dst)  # replaces every page of the live database in one step
        finally:
            dst.close()
            src.close()
        _restore_photos(z, files, db_file.parent / "photos", Path(tmp))
    run_migrations(db_url)
    return info


def _restore_photos(z: zipfile.ZipFile, files: dict[str, object], folder: Path, tmp: Path) -> None:
    """Put back the photos a backup carries. A photo whose name or checksum is wrong is
    skipped (the database row then shows it as missing) rather than failing the restore."""
    for name, meta in files.items():
        if not PHOTO_NAME.match(name) or not isinstance(meta, dict):
            continue
        try:
            info = z.getinfo(name)
        except KeyError:
            continue
        if info.file_size > MAX_PHOTO_BYTES:
            continue
        staged = tmp / Path(name).name
        try:
            _extract_capped(z, info, staged)
        except BackupError:
            continue
        if staged.stat().st_size > MAX_PHOTO_BYTES or _sha256(staged) != meta.get("sha256"):
            continue
        folder.mkdir(parents=True, exist_ok=True)
        staged.replace(folder / staged.name)


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
