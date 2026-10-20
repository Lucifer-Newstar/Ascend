# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for the ASCEND sidecar.
#
#   cd services/sidecar
#   uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm
#
# Output: dist/ascend-sidecar/ascend-sidecar(.exe) plus an _internal/ folder
# ("onedir": starts faster than a single-file exe, which unpacks to %TEMP% on
# every launch). electron-builder copies this folder to resources/sidecar.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent  # services/sidecar
sys.path.insert(0, str(ROOT))  # so collect_submodules("app") can import the package

hiddenimports = (
    collect_submodules("app")
    # uvicorn picks these at runtime by name, so PyInstaller can't see them.
    + collect_submodules("uvicorn")
    + ["alembic.runtime.migration", "alembic.ddl.sqlite", "logging.config"]
)

a = Analysis(
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT)],
    # Alembic reads migrations as source files at runtime, so ship them as data.
    datas=[(str(ROOT / "alembic.ini"), "."), (str(ROOT / "alembic"), "alembic")],
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "mypy", "ruff"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ascend-sidecar",
    console=True,  # no window is shown: Electron spawns it with windowsHide
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ascend-sidecar", upx=False)
