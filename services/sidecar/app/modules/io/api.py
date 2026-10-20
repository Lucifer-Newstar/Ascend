"""Import and export endpoints (ADR-0010)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.io import backup, formats, importer
from app.modules.io.schemas import (
    BackupIn,
    BackupOut,
    ImportIn,
    ImportReport,
    RestoreIn,
    RestoreOut,
)
from app.modules.progress import history

router = APIRouter(tags=["import-export"])


# --- export -----------------------------------------------------------------------


@router.get("/export/json")
def export_json(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> dict[str, Any]:
    """Everything as one JSON document (profile, workouts, meals, metrics)."""
    return history.export_json(db, now)


@router.get("/export/csv/{kind}")
def export_csv(kind: Literal["workouts", "meals"], db: Session = Depends(get_db)) -> Response:
    """One table as CSV, with a download filename."""
    return Response(
        content=history.export_csv(db, kind),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ascend-{kind}.csv"'},
    )


# --- import -----------------------------------------------------------------------


def _run(
    parsed: tuple[formats.Format, list[formats.ImportedSet]],
    body: ImportIn,
    db: Session,
    bus: EventBus,
) -> ImportReport:
    fmt, rows = parsed
    if not rows:
        raise HTTPException(422, "the file has a header but no sets")
    return importer.run_import(
        db, bus, fmt, rows, dry_run=body.dry_run, include_warmups=body.include_warmups
    )


@router.post("/import/strong", response_model=ImportReport)
def import_strong(
    body: ImportIn, db: Session = Depends(get_db), bus: EventBus = Depends(get_bus)
) -> ImportReport:
    """Import a Strong CSV export (classic or 2025 layout). `dry_run` (default true)
    returns the report without writing anything."""
    try:
        fmt = formats.detect_format(body.csv)
        rows = formats.parse_strong(body.csv, unit=body.unit)
    except formats.ImportFormatError as err:
        raise HTTPException(422, str(err)) from err
    return _run((fmt, rows), body, db, bus)


@router.post("/import/hevy", response_model=ImportReport)
def import_hevy(
    body: ImportIn, db: Session = Depends(get_db), bus: EventBus = Depends(get_bus)
) -> ImportReport:
    """Import a Hevy CSV export. `dry_run` (default true) only reports."""
    try:
        rows = formats.parse_hevy(body.csv)
    except formats.ImportFormatError as err:
        raise HTTPException(422, str(err)) from err
    return _run(("hevy_csv", rows), body, db, bus)


# --- backup / restore -----------------------------------------------------------------


def _backup_out(info: backup.BackupInfo) -> BackupOut:
    return BackupOut(
        path=str(info.path),
        size_bytes=info.size_bytes,
        sha256=info.sha256,
        created_at=info.created_at,
        schema_revision=info.schema,
        app_version=info.app_version,
        reason=info.reason,
    )


def _dirs(request: Request) -> tuple[Path, Path]:
    """(live database file, backups folder) for this sidecar."""
    try:
        db_file = backup.sqlite_path(request.app.state.engine)
    except backup.BackupError as err:
        raise HTTPException(409, str(err)) from err
    return db_file, backup.backups_dir(request.app.state.settings.data_dir)


@router.post("/backup", response_model=BackupOut, status_code=201)
def create_backup(
    request: Request, body: BackupIn | None = None, now: datetime = Depends(get_now)
) -> BackupOut:
    """Write a .ascendbak (SQLite snapshot + manifest with SHA-256) to the backups folder."""
    if body is not None and body.password:
        raise HTTPException(422, "password-protected backups are not supported yet")
    db_file, folder = _dirs(request)
    try:
        return _backup_out(backup.create_backup(db_file, folder, now))
    except backup.BackupError as err:
        raise HTTPException(409, str(err)) from err


@router.get("/backups", response_model=list[BackupOut])
def list_backups(request: Request) -> list[BackupOut]:
    """Backups in the backups folder, newest first (manual and pre-migration)."""
    _, folder = _dirs(request)
    return [_backup_out(i) for i in backup.list_backups(folder)]


@router.post("/restore", response_model=RestoreOut)
def restore_backup(
    body: RestoreIn, request: Request, now: datetime = Depends(get_now)
) -> RestoreOut:
    """Restore a .ascendbak over the current data. The current data is backed up first
    (reason "pre-restore"), so a mistaken restore can itself be undone."""
    if body.password:
        raise HTTPException(422, "password-protected backups are not supported yet")
    path = Path(body.path)
    if path.suffix != backup.SUFFIX:
        raise HTTPException(422, f"choose a {backup.SUFFIX} file")
    db_file, folder = _dirs(request)
    try:
        if not path.exists():
            raise backup.BackupError("that backup file does not exist")
        backup.read_info(path)  # refuse a bad file before touching anything
        safety = backup.create_backup(db_file, folder, now, reason="pre-restore")
        info = backup.restore_backup(path, db_file, request.app.state.settings.resolved_db_url)
    except backup.BackupError as err:
        raise HTTPException(422, str(err)) from err
    return RestoreOut(
        restored_from=str(path),
        backup_created_at=info.created_at,
        schema_revision=info.schema,
        safety_backup=str(safety.path),
    )
