"""Fail when a built sidecar carries development tooling (seed_demo, app.devtools).

    uv run python packaging/check_bundle.py            # dist/ascend-sidecar
    uv run python packaging/check_bundle.py path/to/ascend-sidecar

Scans every file of the onedir build (the executable, the PYZ archive inside it and
_internal/) for the forbidden module names, as raw bytes, so it needs no PyInstaller.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bundle_rules import FORBIDDEN_IN_BUNDLE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def offenders(folder: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    needles = [n.encode() for n in FORBIDDEN_IN_BUNDLE]
    for f in sorted(p for p in folder.rglob("*") if p.is_file()):
        if any(n.decode() in f.as_posix() for n in needles):
            found.append((str(f.relative_to(folder)), "file name"))
            continue
        data = f.read_bytes()
        for n in needles:
            if n in data:
                found.append((str(f.relative_to(folder)), n.decode()))
    return found


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "ascend-sidecar"
    if not folder.is_dir():
        print(f"no build at {folder}", file=sys.stderr)
        return 2
    bad = offenders(folder)
    for path, what in bad:
        print(f"dev tooling in the bundle: {path} ({what})", file=sys.stderr)
    if not bad:
        print(f"ok: no dev tooling in {folder}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
