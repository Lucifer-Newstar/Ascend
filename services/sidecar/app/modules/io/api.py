"""Import and export endpoints (ADR-0010)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.io import formats, importer
from app.modules.io.schemas import ImportIn, ImportReport
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
