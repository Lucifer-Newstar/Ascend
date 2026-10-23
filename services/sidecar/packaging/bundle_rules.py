"""What goes into the frozen sidecar, kept apart from the spec so tests can check it.

Development tooling never ships: app.devtools (seed_demo writes fake history into a
data folder) is left out of the module list and excluded outright, and the test and
lint tools are excluded too. tests/unit/test_packaging.py and packaging/check_bundle.py
hold the build to this.
"""

from __future__ import annotations

from collections.abc import Iterable

# Never inside the app: dev-only code, test and lint tools, GUI toolkits we do not use.
DEV_ONLY_PACKAGES = ("app.devtools",)

EXCLUDES = [
    *DEV_ONLY_PACKAGES,
    "tkinter",
    "pytest",
    "_pytest",
    "mypy",
    "ruff",
    "IPython",
    "pydoc_data",
    "lib2to3",
    "PyInstaller",
]

# Names that must not appear anywhere in a built bundle.
FORBIDDEN_IN_BUNDLE = ("seed_demo", "app.devtools")


def is_dev_only(module: str) -> bool:
    return any(module == p or module.startswith(p + ".") for p in DEV_ONLY_PACKAGES)


def app_modules(found: Iterable[str]) -> list[str]:
    """The app's own modules to bundle: everything collected minus dev-only ones."""
    return [m for m in found if not is_dev_only(m)]
