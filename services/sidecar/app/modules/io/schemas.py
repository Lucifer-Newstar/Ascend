from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import StrictIn

# 20 MB of CSV is roughly ten years of daily training in Strong; anything bigger is
# almost certainly the wrong file.
MAX_CSV_CHARS = 20_000_000


class ImportIn(StrictIn):
    """The CSV travels as text: renderer -> IPC -> main -> sidecar carries JSON only."""

    csv: str = Field(min_length=1, max_length=MAX_CSV_CHARS)
    dry_run: bool = True
    unit: Literal["kg", "lb"] = Field(
        default="kg", description="Weight unit for Strong's 2025 export, which has no unit column"
    )
    include_warmups: bool = False


class ImportReport(BaseModel):
    format: Literal["strong_csv", "strong_csv_2025", "hevy_csv", "ascend_plan_csv"]
    workouts: int
    sets: int
    unmatched_exercises: list[str] = []
    warnings: list[str] = []
    dry_run: bool
    skipped_duplicates: int = 0
    skipped_warmups: int = 0
    matched_exercises: dict[str, str] = {}


class BackupIn(StrictIn):
    password: str | None = Field(
        default=None, description="Optional AES-256 password; not supported yet (422)"
    )


class BackupOut(BaseModel):
    path: str
    size_bytes: int
    sha256: str
    created_at: datetime
    schema_revision: str
    app_version: str
    reason: Literal["manual", "pre-migration"] | str = "manual"


class RestoreIn(StrictIn):
    path: str = Field(min_length=1, max_length=1024)
    password: str | None = None


class RestoreOut(BaseModel):
    restored_from: str
    backup_created_at: datetime
    schema_revision: str
    safety_backup: str
