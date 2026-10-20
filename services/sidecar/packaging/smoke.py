"""Smoke-test a built sidecar: start it, wait for /health, stop it via /shutdown.

    uv run python packaging/smoke.py              # dist/ascend-sidecar/ascend-sidecar(.exe)
    uv run python packaging/smoke.py path/to/ascend-sidecar.exe

Uses only the standard library, so it runs on a bare CI image. Exit status 0
means the frozen build imports everything it needs, applies the migrations to a
fresh data folder, answers an authenticated request and shuts down cleanly.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "smoke-token"


def default_binary() -> Path:
    name = "ascend-sidecar.exe" if os.name == "nt" else "ascend-sidecar"
    return ROOT / "dist" / "ascend-sidecar" / name


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def call(port: int, method: str, path: str) -> tuple[int, dict[str, object]]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, {}


def run(binary: Path, timeout: float = 60.0) -> int:
    if not binary.exists():
        print(f"smoke: {binary} does not exist; build it first", file=sys.stderr)
        return 2
    port = free_port()
    with tempfile.TemporaryDirectory() as data:
        env = {**os.environ, "ASCEND_PORT": str(port), "ASCEND_DATA_DIR": data}
        env.pop("ASCEND_TOKEN", None)  # the real app hands the token over stdin
        proc = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, env=env)
        assert proc.stdin is not None
        proc.stdin.write(f"{TOKEN}\n".encode())
        proc.stdin.close()
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    print(f"smoke: sidecar exited early with {proc.returncode}", file=sys.stderr)
                    return 1
                try:
                    status, body = call(port, "GET", "/health")
                except OSError:
                    time.sleep(0.5)
                    continue
                if status == 200 and body.get("status") == "ok":
                    break
                time.sleep(0.5)
            else:
                print("smoke: /health never answered ok", file=sys.stderr)
                return 1
            print(f"smoke: healthy {body}")
            if call(port, "GET", "/exercises")[0] != 200:
                print("smoke: authenticated request failed", file=sys.stderr)
                return 1
            call(port, "POST", "/shutdown")
            proc.wait(timeout=15)
            print(f"smoke: stopped with exit code {proc.returncode}")
            return 0
        finally:
            if proc.poll() is None:
                proc.kill()


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]) if len(sys.argv) > 1 else default_binary()))
