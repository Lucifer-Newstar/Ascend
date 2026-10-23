"""v1.1: development runs never share the installed app's data folder."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import config
from app.devtools import seed_demo


def test_dev_default_is_separate_from_the_installed_app(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv("ASCEND_DATA_DIR", raising=False)
    assert config.installed_data_dir() == tmp_path / "ASCEND" / "data"
    assert config.load_settings().data_dir == tmp_path / "ASCEND-dev" / "data"


def test_electron_folder_wins(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ASCEND_DATA_DIR", str(tmp_path / "x"))
    assert config.load_settings().data_dir == tmp_path / "x"


def test_seed_refuses_the_installed_app_folder(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    app_dir = tmp_path / "ASCEND" / "data"
    with pytest.raises(seed_demo.RefusedTarget):
        seed_demo.check_target(app_dir, "")
    seed_demo.check_target(app_dir, "", allow_app_data=True)  # explicit opt-in
    seed_demo.check_target(tmp_path / "ASCEND-dev" / "data", "")  # the dev folder is fine
    seed_demo.check_target(app_dir, "sqlite:///scratch.db")  # an explicit DB URL is fine
