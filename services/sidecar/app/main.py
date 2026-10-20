"""FastAPI application factory: wires settings, DB, event bus and module routers."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import Settings, load_settings
from app.core.db import checkpoint_wal, make_engine, make_session_factory
from app.core.events import EventBus
from app.core.migrate import current_revision, head_revision, run_migrations
from app.core.security import TokenAuthMiddleware
from app.modules.coach.api import router as coach_router
from app.modules.gamification import service as gamification_service
from app.modules.gamification.api import router as game_router
from app.modules.nutrition.api import router as nutrition_router
from app.modules.progress import service as progress_service
from app.modules.progress.api import router as progress_router
from app.modules.workouts.api import deload_router, exercises_router, prs_router
from app.modules.workouts.api import router as workouts_router

log = logging.getLogger("ascend")

# Vite dev server origins. Only used with --dev (browser development without Electron).
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def _exit_soon() -> None:
    """SIGTERM ourselves after the response is sent; uvicorn then exits cleanly."""
    threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()


def build_bus() -> EventBus:
    """Subscribe module handlers. Order matters: muscle load is written before XP/quests run."""
    bus = EventBus()
    progress_service.register(bus)
    gamification_service.register(bus)
    return bus


def create_app(
    settings: Settings | None = None,
    clock: Callable[[], datetime] | None = None,
    migrate: bool = True,
) -> FastAPI:
    settings = settings or load_settings()
    db_url = settings.resolved_db_url
    if migrate:
        run_migrations(db_url)

    app = FastAPI(
        title="ASCEND sidecar",
        version=__version__,
        description="Local API for the ASCEND desktop app. Bound to 127.0.0.1 only.",
    )
    engine = make_engine(db_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.bus = build_bus()
    app.state.clock = clock or datetime.now
    # Tests replace this so POST /shutdown does not stop the test process.
    app.state.request_exit = _exit_soon

    app.add_middleware(TokenAuthMiddleware, token=settings.token)
    if settings.dev:
        app.add_middleware(
            CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"]
        )

    head = head_revision()

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Open endpoint polled by Electron main. 'degraded' means the API is up but the
        database is unreachable or behind the newest migration."""
        db_status, mode, current = "ok", "unknown", None
        try:
            with engine.connect() as conn:
                mode = str(conn.exec_driver_sql("PRAGMA journal_mode").scalar())
                current = current_revision(conn)
        except Exception as exc:  # pragma: no cover - exercised by the corrupt-db test
            log.error("health: database check failed: %s", exc)
            db_status = "error"
        if db_status == "ok" and current != head:
            db_status = "migration_pending"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "version": __version__,
            "journal_mode": mode,
            "db": db_status,
            "migration": current or "none",
            "migration_head": head,
        }

    @app.post("/shutdown", tags=["system"])
    def shutdown() -> dict[str, str]:
        """Graceful stop requested by Electron main before it quits.

        The WAL is checkpointed into the main database file first, so a copy of
        ascend.db taken after the app closes is complete on its own."""
        checkpoint = checkpoint_wal(engine)
        app.state.request_exit()
        return {"status": "stopping", "wal_checkpoint": checkpoint}

    for router in (
        workouts_router,
        exercises_router,
        prs_router,
        deload_router,
        nutrition_router,
        game_router,
        progress_router,
        coach_router,
    ):
        app.include_router(router)
    return app
