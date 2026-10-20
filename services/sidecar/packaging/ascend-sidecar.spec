# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for the ASCEND sidecar.
#
#   cd services/sidecar
#   uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm
#
# Output: dist/ascend-sidecar/ascend-sidecar(.exe) plus an _internal/ folder
# ("onedir": starts faster than a single-file exe, which unpacks to %TEMP% on
# every launch). electron-builder copies this folder to resources/sidecar.
#
# Check a build with:  uv run python packaging/smoke.py
import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent  # services/sidecar
sys.path.insert(0, str(ROOT))  # so collect_submodules("app") can import the package

# One source of truth for the version: app/__init__.py.
VERSION = re.search(
    r'__version__ = "([^"]+)"', (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
).group(1)


def windows_version_info():
    """Details tab of the exe (Properties -> Details), so support can read the build."""
    if sys.platform != "win32":
        return None
    from PyInstaller.utils.win32 import versioninfo as vi

    nums = tuple(int(p) for p in re.findall(r"\d+", VERSION)[:3]) + (0,)
    strings = [
        vi.StringStruct("CompanyName", "The ASCEND team"),
        vi.StringStruct("FileDescription", "ASCEND local engine"),
        vi.StringStruct("FileVersion", VERSION),
        vi.StringStruct("InternalName", "ascend-sidecar"),
        vi.StringStruct("OriginalFilename", "ascend-sidecar.exe"),
        vi.StringStruct("ProductName", "ASCEND"),
        vi.StringStruct("ProductVersion", VERSION),
    ]
    return vi.VSVersionInfo(
        ffi=vi.FixedFileInfo(filevers=nums, prodvers=nums),
        kids=[
            vi.StringFileInfo([vi.StringTable("040904B0", strings)]),
            vi.VarFileInfo([vi.VarStruct("Translation", [1033, 1200])]),
        ],
    )


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
    datas=[
        (str(ROOT / "alembic.ini"), "."),
        (str(ROOT / "alembic"), "alembic"),
        # Bundled exercise library (free-exercise-db), read by migration 0010.
        (
            str(ROOT / "app" / "modules" / "workouts" / "library_data"),
            "app/modules/workouts/library_data",
        ),
    ],
    hiddenimports=hiddenimports,
    # Dev and test tooling never runs inside the app; keeping it out shrinks the
    # install and the attack surface.
    excludes=[
        "tkinter",
        "pytest",
        "_pytest",
        "mypy",
        "ruff",
        "IPython",
        "pydoc_data",
        "lib2to3",
        "PyInstaller",
    ],
    noarchive=False,
    optimize=1,  # strip asserts and __debug__ blocks from the bundled bytecode
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ascend-sidecar",
    console=True,  # no window is shown: Electron spawns it with windowsHide
    upx=False,  # UPX-packed exes trip antivirus heuristics far more often
    version=windows_version_info(),
)
coll = COLLECT(exe, a.binaries, a.datas, name="ascend-sidecar", upx=False)
