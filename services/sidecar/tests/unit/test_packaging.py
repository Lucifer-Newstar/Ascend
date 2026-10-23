"""seed_demo (and the rest of app.devtools) is never packaged into the app."""

from __future__ import annotations

import importlib.util
import pkgutil
import sys
from pathlib import Path

import app

PACKAGING = Path(__file__).resolve().parents[2] / "packaging"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGING / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rules = _load("bundle_rules")


def _all_app_modules() -> list[str]:
    return [m.name for m in pkgutil.walk_packages(app.__path__, "app.")]


def test_seed_demo_exists_but_is_filtered_out() -> None:
    found = _all_app_modules()
    assert "app.devtools.seed_demo" in found  # the filter has something to remove
    bundled = rules.app_modules(found)
    assert not [m for m in bundled if m.startswith("app.devtools")]
    assert "app.main" in bundled


def test_devtools_is_excluded_outright() -> None:
    assert "app.devtools" in rules.EXCLUDES
    for tool in ("pytest", "mypy", "ruff", "PyInstaller"):
        assert tool in rules.EXCLUDES


def test_the_spec_uses_the_rules() -> None:
    spec = (PACKAGING / "ascend-sidecar.spec").read_text("utf-8")
    assert 'app_modules(collect_submodules("app"))' in spec
    assert "excludes=EXCLUDES" in spec
    assert 'collect_submodules("app")\n' not in spec.replace(
        'app_modules(collect_submodules("app"))', ""
    )


def test_nothing_in_the_app_imports_devtools() -> None:
    root = Path(app.__file__).parent
    for f in root.rglob("*.py"):
        if "devtools" in f.parts:
            continue
        text = f.read_text("utf-8")
        assert "app.devtools" not in text and "from app import devtools" not in text, f


def test_bundle_checker_flags_seed_demo(tmp_path: Path) -> None:
    check = _load("check_bundle")
    (tmp_path / "_internal").mkdir()
    (tmp_path / "_internal" / "base_library.zip").write_bytes(b"...app.main...")
    assert check.offenders(tmp_path) == []
    (tmp_path / "ascend-sidecar").write_bytes(b"\x00PYZ app.devtools.seed_demo \x00")
    assert check.offenders(tmp_path)
