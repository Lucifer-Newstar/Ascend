"""Erase the user's data and keep the reference libraries ("start fresh").

Used by the trainer's "start fresh" flow and Settings > Erase my data, and by the demo
seeder's --wipe. What stays: the exercise library (minus exercises the user added), the
food table and the schema itself; with `keep_preferences`, also the app preferences
(theme, units, motion, AI switch, chosen trainer). Everything else in the database is
the user's and goes, as do their progress photos on disk.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.modules.workouts.models import Exercise, ExerciseMuscle

# Reference tables that ship with the app (filled by migrations, not by the user).
REFERENCE_TABLES = frozenset({"exercises", "exercise_muscles", "foods", "alembic_version"})

# App preferences kept by "start fresh"; every other settings key is about the user.
PREFERENCE_KEYS = frozenset(
    {
        "ai_enabled",
        "units",
        "theme",
        "reduce_motion",
        "online_lookup",
        "trainer",
        "trainer_id",
        "team_handoff",
        "coach_model",
        "hide_calories",
    }
)

PHOTOS_DIR = "photos"


def erase_user_data(
    db: Session, *, keep_preferences: bool = True, data_dir: Path | None = None
) -> dict[str, int]:
    """Delete every user row (and photo files under `data_dir`). Returns rows per table."""
    # Imported here: settings rows are filtered by key, so the model is needed by name.
    from app.modules.progress.models import Setting

    counts: dict[str, int] = {}
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in REFERENCE_TABLES:
            continue
        if table.name == "settings" and keep_preferences:
            stmt = delete(Setting).where(Setting.key.not_in(PREFERENCE_KEYS))
            counts["settings"] = db.execute(stmt).rowcount or 0  # type: ignore[attr-defined]
            continue
        counts[table.name] = db.execute(table.delete()).rowcount or 0  # type: ignore[attr-defined]
    # The library stays; exercises the user added are user data and go too.
    custom_ids = select(Exercise.id).where(Exercise.is_custom.is_(True))
    db.execute(delete(ExerciseMuscle).where(ExerciseMuscle.exercise_id.in_(custom_ids)))
    counts["custom_exercises"] = (
        db.execute(delete(Exercise).where(Exercise.is_custom.is_(True))).rowcount or 0  # type: ignore[attr-defined]
    )
    # v1.2: foods the user added are user data as well (their meals are gone by now).
    from app.modules.nutrition.models import Food
    from app.modules.nutrition.service import CUSTOM_SOURCE

    counts["custom_foods"] = (
        db.execute(delete(Food).where(Food.source == CUSTOM_SOURCE)).rowcount or 0  # type: ignore[attr-defined]
    )
    db.commit()
    if data_dir is not None:
        photos = data_dir / PHOTOS_DIR
        if photos.is_dir():
            counts["photo_files"] = sum(1 for p in photos.rglob("*") if p.is_file())
            shutil.rmtree(photos, ignore_errors=True)
    return {k: v for k, v in counts.items() if v}
