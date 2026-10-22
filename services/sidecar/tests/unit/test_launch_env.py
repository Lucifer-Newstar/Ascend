"""Security review H3: the packaged sidecar can't be steered through its environment."""

from __future__ import annotations

import io
import os

import pytest

from app.__main__ import prepare_env
from app.core.config import load_settings


def test_packaged_ignores_env_token_host_and_db(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {
        "ASCEND_TOKEN": "dev",
        "ASCEND_HOST": "0.0.0.0",
        "ASCEND_DB_URL": "sqlite:///elsewhere.db",
        "ASCEND_DEV": "1",
        "ASCEND_PORT": "50123",
    }
    prepare_env(env, io.StringIO("s3cret-from-electron\n"), dev=False, frozen=True)
    assert env["ASCEND_TOKEN"] == "s3cret-from-electron"
    assert env["ASCEND_HOST"] == "127.0.0.1"
    assert "ASCEND_DB_URL" not in env and "ASCEND_DEV" not in env
    for name in list(os.environ):
        if name.startswith("ASCEND_"):
            monkeypatch.delenv(name)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = load_settings()
    assert (s.token, s.host, s.db_url, s.dev, s.port) == (
        "s3cret-from-electron",
        "127.0.0.1",
        "",
        False,
        50123,
    )


def test_packaged_requires_a_token_on_stdin() -> None:
    with pytest.raises(SystemExit):
        prepare_env({"ASCEND_TOKEN": "dev"}, io.StringIO(""), dev=False, frozen=True)


def test_packaged_refuses_dev_mode() -> None:
    with pytest.raises(SystemExit):
        prepare_env({}, io.StringIO("t\n"), dev=True, frozen=True)


def test_source_run_keeps_the_developer_workflow() -> None:
    env: dict[str, str] = {"ASCEND_TOKEN": "mine"}
    prepare_env(env, io.StringIO("ignored\n"), dev=False, frozen=False)
    assert env["ASCEND_TOKEN"] == "mine"
    env = {}
    prepare_env(env, io.StringIO(""), dev=True, frozen=False)
    assert env == {"ASCEND_TOKEN": "dev", "ASCEND_DEV": "1"}
    env = {}
    prepare_env(env, io.StringIO("from-stdin\n"), dev=False, frozen=False)
    assert env["ASCEND_TOKEN"] == "from-stdin"
