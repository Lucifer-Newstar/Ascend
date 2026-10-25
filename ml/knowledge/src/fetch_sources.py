"""Download the two large knowledge-base sources, pinned by SHA-256.

  pag2.pdf       Physical Activity Guidelines for Americans, 2nd ed. (15 MB, public domain)
  sr_legacy.zip  USDA FoodData Central SR Legacy CSV, April 2018 release (6 MB, CC0)

Neither is committed; build_corpus.py reads them from knowledge/raw/.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw"
FILES = {
    "pag2.pdf": (
        "https://odphp.health.gov/sites/default/files/2019-09/"
        "Physical_Activity_Guidelines_2nd_edition.pdf",
        "0147d4dfc5ae76613a8b8d9d1c95244477527989f1d841845866ae5b5340cda5",
    ),
    "sr_legacy.zip": (
        "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip",
        "b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0",
    ),
}


def fetch(src: Path | None = None) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in FILES.items():
        out = RAW / name
        if src is not None and (src / name).exists() and not out.exists():
            shutil.copy(src / name, out)
        if not out.exists():
            print(f"downloading {url}")
            with urllib.request.urlopen(url, timeout=300) as r, out.open("wb") as f:  # noqa: S310
                shutil.copyfileobj(r, f)
        got = hashlib.sha256(out.read_bytes()).hexdigest()
        if got != digest:
            out.unlink()
            raise SystemExit(f"{name}: sha256 {got} != pinned {digest}")
        print(f"ok {name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-dir", type=Path)
    fetch(ap.parse_args().from_dir)
