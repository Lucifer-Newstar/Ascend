"""Runtime settings, read once from environment variables.

Electron main sets these when it spawns the sidecar. Nothing here talks to the
network; the only optional outbound call is to a local Ollama on localhost
(a remote Ollama only with ASCEND_OLLAMA_ALLOW_REMOTE=1, see normalize_ollama_host).
"""

from __future__ import annotations

import ipaddress
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

log = logging.getLogger("ascend")

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_PORT = 11434


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_ollama_host(raw: str | None, allow_remote: bool = False) -> str:
    """OLLAMA_HOST as a base URL for httpx, or "" when it can't or mustn't be used.

    Follows Ollama's own convention: the value may omit the scheme ("127.0.0.1:11434",
    "localhost") and then defaults to http and port 11434; 0.0.0.0 / :: mean "listen
    everywhere" on the server side, so the client connects to loopback. A host that is
    not loopback is refused unless `allow_remote` (the coach would send health data
    there over plain HTTP).
    """
    text = (raw or "").strip()
    if not text:
        return DEFAULT_OLLAMA_HOST
    has_scheme = "://" in text
    if not has_scheme and text.count(":") > 1 and not text.startswith("["):
        text = f"[{text}]"  # a bare IPv6 address such as "::" or "::1"
    try:
        parts = urlsplit(text if has_scheme else f"http://{text}")
        port = parts.port
    except ValueError:
        log.warning("OLLAMA_HOST %r is not a valid address; the AI coach is off", text)
        return ""
    host = parts.hostname or ""
    if parts.scheme not in ("http", "https") or not host or parts.username or parts.password:
        log.warning("OLLAMA_HOST %r is not a valid address; the AI coach is off", text)
        return ""
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1" if host == "0.0.0.0" else "::1"
    if port is None:
        port = {"http": 80, "https": 443}[parts.scheme] if has_scheme else OLLAMA_PORT
    if not _is_loopback(host) and not allow_remote:
        log.warning(
            "OLLAMA_HOST %r is not on this PC; the AI coach stays off "
            "(set ASCEND_OLLAMA_ALLOW_REMOTE=1 to use a remote Ollama)",
            text,
        )
        return ""
    shown = f"[{host}]" if ":" in host else host
    return f"{parts.scheme}://{shown}:{port}"


# The installed app's folder: Electron always passes it as ASCEND_DATA_DIR
# (%APPDATA%\ASCEND\data on Windows). Development runs that do not pass a folder
# (`make dev-sidecar`, `make seed`, `make migrate`) use a separate "-dev" folder, so demo
# data from a developer machine can never end up in the installed app (v1.1 fix: the
# 1.0.0 installer opened whatever `make seed` had written to %APPDATA%\ASCEND).
APP_FOLDER = "ASCEND"
DEV_FOLDER = "ASCEND-dev"


def installed_data_dir() -> Path:
    """Where the installed app keeps its data (Windows) or would (elsewhere)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_FOLDER / "data"
    return Path.home() / ".ascend" / "data"


def _default_data_dir() -> Path:
    # Windows: %APPDATA%\ASCEND-dev\data. Elsewhere: ~/.ascend-dev/data
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / DEV_FOLDER / "data"
    return Path.home() / ".ascend-dev" / "data"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    db_url: str = ""
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""
    dev: bool = False
    ollama_host: str = DEFAULT_OLLAMA_HOST
    coach_model: str = "qwen3:4b"
    coach_timeout_s: float = 20.0
    # Optional vision model for progress-photo feedback (off until the user pulls it).
    vision_model: str = "qwen3-vl:2b"

    @property
    def resolved_db_url(self) -> str:
        if self.db_url:
            return self.db_url
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(self.data_dir / 'ascend.db').as_posix()}"


def load_settings() -> Settings:
    env = os.environ
    data_dir = Path(env["ASCEND_DATA_DIR"]) if env.get("ASCEND_DATA_DIR") else _default_data_dir()
    return Settings(
        data_dir=data_dir,
        db_url=env.get("ASCEND_DB_URL", ""),
        host=env.get("ASCEND_HOST", "127.0.0.1"),
        port=int(env.get("ASCEND_PORT", "8765")),
        token=env.get("ASCEND_TOKEN", ""),
        dev=env.get("ASCEND_DEV", "") == "1",
        ollama_host=normalize_ollama_host(
            env.get("OLLAMA_HOST"), allow_remote=env.get("ASCEND_OLLAMA_ALLOW_REMOTE", "") == "1"
        ),
        coach_model=env.get("ASCEND_COACH_MODEL", "qwen3:4b"),
        vision_model=env.get("ASCEND_VISION_MODEL", "qwen3-vl:2b"),
    )
