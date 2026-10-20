"""Alembic environment.

The app calls `run_migrations(url)` (app/core/migrate.py) at startup, which
passes the URL through `config.attributes`. From the CLI the URL comes from
the same settings loader the app uses.
"""

from __future__ import annotations

from alembic import context
from app.core.config import load_settings
from app.core.db import make_engine
from app.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    return config.attributes.get("db_url") or load_settings().resolved_db_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, render_as_batch=True,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = make_engine(_url())  # same PRAGMAs (WAL, foreign keys) as the app
    with engine.connect() as connection:
        # render_as_batch: SQLite can't ALTER most columns, so Alembic copies tables instead.
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
