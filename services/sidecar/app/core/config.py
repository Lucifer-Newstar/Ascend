"""Runtime settings, read once from environment variables.

Electron main sets these when it spawns the sidecar. Nothing here talks to the
network; the only optional outbound call is to a local Ollama on localhost.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    # Windows: %APPDATA%\ASCEND ; elsewhere: ~/.ascend
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ASCEND"
    return Path.home() / ".ascend"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    db_url: str = ""
    host: str = "127.0.0.1"
    port: int = 8765
    token: str = ""
    dev: bool = False
    ollama_host: str = "http://127.0.0.1:11434"
    coach_model: str = "qwen3:4b"
    coach_timeout_s: float = 20.0

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
        ollama_host=env.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        coach_model=env.get("ASCEND_COACH_MODEL", "qwen3:4b"),
    )
