"""Entry point: `python -m app` (dev) or the PyInstaller-built ascend-sidecar.exe.

Electron main starts this process with ASCEND_PORT set and writes the auth
token as the first line on stdin, so the token never appears in the process
list or in environment dumps. `--dev` uses port 8765 and token "dev".
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="ascend-sidecar")
    parser.add_argument("--dev", action="store_true", help="port 8765, token 'dev', CORS for Vite")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    if args.dev:
        os.environ.setdefault("ASCEND_TOKEN", "dev")
        os.environ["ASCEND_DEV"] = "1"
    elif not os.environ.get("ASCEND_TOKEN"):
        token = sys.stdin.readline().strip()
        if not token:
            sys.exit("ascend-sidecar: expected auth token on stdin")
        os.environ["ASCEND_TOKEN"] = token
    if args.port is not None:
        os.environ["ASCEND_PORT"] = str(args.port)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from app.core.config import load_settings
    from app.main import create_app

    settings = load_settings()
    app = create_app(settings)
    # Electron watches stdout for this line in addition to polling /health.
    print(f"ASCEND_SIDECAR_READY port={settings.port}", flush=True)
    # Always 127.0.0.1 on desktops; the dev container sets ASCEND_HOST=0.0.0.0.
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()
