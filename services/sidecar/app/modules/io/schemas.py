from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 20 MB of CSV is roughly ten years of daily training in Strong; anything bigger is
# almost certainly the wrong file.
MAX_CSV_CHARS = 20_000_000


class ImportIn(BaseModel):
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
