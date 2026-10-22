"""Entry point: `python -m app` (dev) or the PyInstaller-built ascend-sidecar.exe.

Electron main starts this process with ASCEND_PORT set and writes the auth
token as the first line on stdin, so the token never appears in the process
list or in environment dumps. `--dev` uses port 8765 and token "dev".

The packaged build (PyInstaller sets `sys.frozen`, which the environment can't fake)
always reads the token from stdin, always binds 127.0.0.1 and ignores the developer
settings ASCEND_TOKEN, ASCEND_HOST, ASCEND_DB_URL and ASCEND_DEV even if they are set.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import MutableMapping
from typing import IO

import uvicorn

# Developer-only settings: honoured by `python -m app`, ignored by the packaged build.
DEV_ONLY_ENV = ("ASCEND_TOKEN", "ASCEND_HOST", "ASCEND_DB_URL", "ASCEND_DEV")


def _read_token(stdin: IO[str]) -> str:
    token = stdin.readline().strip()
    if not token:
        sys.exit("ascend-sidecar: expected auth token on stdin")
    return token


def prepare_env(env: MutableMapping[str, str], stdin: IO[str], dev: bool, frozen: bool) -> None:
    """Set ASCEND_TOKEN (and, packaged, ASCEND_HOST) in `env` for load_settings()."""
    if frozen:
        if dev:
            sys.exit("ascend-sidecar: --dev is not available in the packaged app")
        for name in DEV_ONLY_ENV:
            env.pop(name, None)
        env["ASCEND_TOKEN"] = _read_token(stdin)
        env["ASCEND_HOST"] = "127.0.0.1"
    elif dev:
        env.setdefault("ASCEND_TOKEN", "dev")
        env["ASCEND_DEV"] = "1"
    elif not env.get("ASCEND_TOKEN"):
        env["ASCEND_TOKEN"] = _read_token(stdin)


def main() -> None:
    parser = argparse.ArgumentParser(prog="ascend-sidecar")
    parser.add_argument(
        "--dev", action="store_true", help="port 8765, token 'dev' (Vite proxies /api)"
    )
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    prepare_env(os.environ, sys.stdin, dev=args.dev, frozen=bool(getattr(sys, "frozen", False)))
    if args.port is not None:
        os.environ["ASCEND_PORT"] = str(args.port)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from app.core.config import load_settings
    from app.main import create_app, exit_via

    settings = load_settings()
    app = create_app(settings)
    # Electron watches stdout for this line in addition to polling /health.
    print(f"ASCEND_SIDECAR_READY port={settings.port}", flush=True)
    # Always 127.0.0.1 in the packaged app (prepare_env); only the dev container sets
    # ASCEND_HOST=0.0.0.0, for `python -m app` inside Docker.
    server = uvicorn.Server(
        uvicorn.Config(app, host=settings.host, port=settings.port, log_level="warning")
    )
    # POST /shutdown asks this server to stop instead of signalling the process: on
    # Windows a self-SIGTERM is TerminateProcess and skipped the lifespan shutdown.
    app.state.request_exit = exit_via(server)
    server.run()


if __name__ == "__main__":
    main()
