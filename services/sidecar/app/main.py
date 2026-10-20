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
from app.core.db import make_engine, make_session_factory
from app.core.events import EventBus
from app.core.migrate import run_migrations
from app.core.security import TokenAuthMiddleware
from app.modules.coach.api import router as coach_router
from app.modules.gamification import service as gamification_service
from app.modules.gamification.api import router as game_router
from app.modules.nutrition.api import router as nutrition_router
from app.modules.progress import service as progress_service
from app.modules.progress.api import router as progress_router
from app.modules.workouts.api import exercises_router
from app.modules.workouts.api import router as workouts_router

log = logging.getLogger("ascend")

# Vite dev server origins. Only used with --dev (browser development without Electron).
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


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

    app.add_middleware(TokenAuthMiddleware, token=settings.token)
    if settings.dev:
        app.add_middleware(
            CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"]
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        with engine.connect() as conn:
            mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
        return {"status": "ok", "version": __version__, "journal_mode": str(mode)}

    @app.post("/shutdown", tags=["system"])
    def shutdown() -> dict[str, str]:
        """Graceful stop requested by Electron main before it quits."""
        threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
        return {"status": "stopping"}

    for router in (
        workouts_router,
        exercises_router,
        nutrition_router,
        game_router,
        progress_router,
        coach_router,
    ):
        app.include_router(router)
    return app
