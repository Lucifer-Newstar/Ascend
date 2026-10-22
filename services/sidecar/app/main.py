"""FastAPI application factory: wires settings, DB, event bus and module routers."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import threading
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app import __version__
from app.core import outbox_worker, stream
from app.core.config import Settings, load_settings
from app.core.db import checkpoint_wal, make_engine, make_session_factory
from app.core.events import EventBus
from app.core.migrate import current_revision, head_revision, run_migrations
from app.core.security import TokenAuthMiddleware
from app.modules.coach.api import router as coach_router
from app.modules.gamification import service as gamification_service
from app.modules.gamification.api import router as game_router
from app.modules.intelligence import recovery_service
from app.modules.intelligence.api import router as intelligence_router
from app.modules.io.api import router as io_router
from app.modules.nutrition.api import router as nutrition_router
from app.modules.progress import service as progress_service
from app.modules.progress.api import router as progress_router
from app.modules.skills import service as skills_service
from app.modules.skills.api import router as skills_router
from app.modules.workouts.api import deload_router, exercises_router, plans_router, prs_router
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
    recovery_service.register(bus)
    gamification_service.register(bus)
    skills_service.register(bus)
    return bus


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Run the outbox worker for the life of the server (off when interval is 0)."""
    interval: float = app.state.outbox_interval
    task = None
    if interval > 0:
        task = asyncio.create_task(
            outbox_worker.loop(
                app.state.session_factory,
                lambda: app.state.outbox_consumers,
                lambda: app.state.clock(),
                interval,
            )
        )
    daily = None
    if interval > 0:
        daily = asyncio.create_task(_daily_backups(app))
    try:
        yield
    finally:
        for t in (task, daily):
            if t is not None:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t


DAILY_BACKUP_CHECK_S = 3600.0


def daily_backup_once(app: FastAPI) -> None:
    """Take today's automatic snapshot if it is due (never raises: a backup problem must
    not take the app down; it is logged instead)."""
    from app.modules.io import backup

    try:
        db_file = backup.sqlite_path(app.state.engine)
        info = backup.backup_daily_if_due(
            db_file, backup.backups_dir(app.state.settings.data_dir), app.state.clock()
        )
    except Exception as err:  # noqa: BLE001 - documented as never raising
        log.warning("daily backup failed: %s", err, exc_info=not isinstance(err, OSError))
        return
    if info is not None:
        log.info("daily backup written to %s", info.path)


async def _daily_backups(app: FastAPI) -> None:
    """At start-up and then about hourly: one snapshot per calendar day, 14 kept."""
    while True:
        try:
            await asyncio.to_thread(daily_backup_once, app)
        except Exception:  # noqa: BLE001 - one bad check must not end the loop for the session
            log.exception("daily backup check crashed; trying again in an hour")
        await asyncio.sleep(DAILY_BACKUP_CHECK_S)


def _backup_before_migrating(settings: Settings, db_url: str, now: datetime) -> None:
    """An app update that migrates the schema first saves the old database (ADR-0010)."""
    from app.modules.io import backup

    if not db_url.startswith("sqlite:///"):
        return
    db_file = Path(db_url.removeprefix("sqlite:///"))
    try:
        info = backup.backup_if_behind(db_file, backup.backups_dir(settings.data_dir), now)
    except (OSError, backup.BackupError) as err:  # never block start-up on the safety copy
        log.warning("pre-migration backup failed: %s", err)
        return
    if info is not None:
        log.info("pre-migration backup written to %s (schema %s)", info.path, info.schema)


def create_app(
    settings: Settings | None = None,
    clock: Callable[[], datetime] | None = None,
    migrate: bool = True,
    outbox_interval: float = 2.0,
) -> FastAPI:
    settings = settings or load_settings()
    db_url = settings.resolved_db_url
    if migrate:
        _backup_before_migrating(settings, db_url, (clock or datetime.now)())
        run_migrations(db_url)

    app = FastAPI(
        title="ASCEND sidecar",
        version=__version__,
        description="Local API for the ASCEND desktop app. Bound to 127.0.0.1 only.",
        lifespan=lifespan,
    )
    app.state.outbox_interval = outbox_interval
    # Async consumers of domain events, by name (empty until a module registers one).
    app.state.outbox_consumers = {}
    engine = make_engine(db_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.clock = clock or datetime.now
    app.state.bus = build_bus()
    app.state.bus.outbox = True
    # Read through app.state so tests that swap the clock also move outbox timestamps.
    app.state.bus.clock = lambda: app.state.clock()
    # Tests replace this so POST /shutdown does not stop the test process.
    app.state.request_exit = _exit_soon

    @app.exception_handler(OverflowError)
    async def number_out_of_range(_request: Request, _exc: OverflowError) -> JSONResponse:
        # SQLite integers are 64-bit; a path or query id above 2**63-1 used to surface as a
        # 500 from the driver (review L4). No row can have such an id.
        return JSONResponse(
            status_code=422, content={"detail": "a number in the request is out of range"}
        )

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

    @app.get(
        "/events",
        tags=["system"],
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "text/event-stream; each message is a ServerEvent",
                "content": {
                    "text/event-stream": {"schema": {"$ref": "#/components/schemas/ServerEvent"}}
                },
            }
        },
    )
    async def events(
        request: Request,
        once: bool = False,
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        """Server-sent stream of dashboard changes, completed quests and PRs, read from the
        outbox. Reconnect with Last-Event-ID to resume; `once=true` sends the backlog and
        closes."""
        gen = stream.stream(
            app.state.session_factory,
            stream.parse_last_id(last_event_id),
            once,
            request.is_disconnected,
        )
        return StreamingResponse(
            gen, media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
        )

    for router in (
        workouts_router,
        exercises_router,
        prs_router,
        deload_router,
        plans_router,
        nutrition_router,
        game_router,
        progress_router,
        skills_router,
        coach_router,
        io_router,
        intelligence_router,
    ):
        app.include_router(router)
    return app
