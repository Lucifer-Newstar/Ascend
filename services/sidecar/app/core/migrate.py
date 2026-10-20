"""Run Alembic migrations programmatically (used at sidecar startup and in tests)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

from alembic import command

SIDECAR_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(db_url: str) -> Config:
    cfg = Config(str(SIDECAR_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(SIDECAR_ROOT / "alembic"))
    cfg.attributes["db_url"] = db_url
    return cfg


def run_migrations(db_url: str) -> None:
    command.upgrade(alembic_config(db_url), "head")


def head_revision() -> str:
    """Newest revision shipped with this build (from the migration scripts on disk)."""
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    head = script.get_current_head()
    return head or "none"


def current_revision(conn: Connection) -> str | None:
    """Revision the database is stamped with, or None for an empty database."""
    return MigrationContext.configure(conn).get_current_revision()
