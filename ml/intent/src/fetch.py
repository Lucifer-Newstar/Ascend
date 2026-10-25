"""Fetch the two public text sources for the intent model and keep only what it needs.

* Fitness Stack Exchange data dump (archive.org, April 2024; CC BY-SA 2.5/3.0/4.0 per post,
  the licence is recorded per question). Only Posts.xml is unpacked; every question becomes
  one JSON line (id, title, tags, licence, the first 300 characters of its body for the
  leak check). The 35 MB archive and the 45 MB XML are deleted afterwards.
* CLINC150 data_full.json (github.com/clinc/oos-eval, CC BY 3.0): out-of-scope queries and
  a few in-scope ones that map onto ASCEND intents (see clinc.py).

Both downloads are pinned by SHA-256, so a changed upstream file fails loudly instead of
silently changing the dataset.

    python intent/src/fetch.py                 # download into intent/raw/
    python intent/src/fetch.py --from-dir DIR  # use fitness.7z + clinc_data_full.json in DIR
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"

SOURCES = {
    "fitness.7z": (
        "https://archive.org/download/stackexchange/fitness.stackexchange.com.7z",
        "5fe08b64b0fbdc917aa66217af5d162270a59159eccd2fff8bc287674d4f52a7",
    ),
    "clinc_data_full.json": (
        "https://raw.githubusercontent.com/clinc/oos-eval/master/data/data_full.json",
        "36923c3705a59e08fe9c3883d8bc2dd966ef93e22cb78ac41171782a698d56e0",
    ),
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(name: str, dest: Path) -> Path:
    url, digest = SOURCES[name]
    out = dest / name
    if not out.exists():
        print(f"downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as r, out.open("wb") as f:  # noqa: S310
            shutil.copyfileobj(r, f)
    got = sha256(out)
    if got != digest:
        raise SystemExit(f"{name}: sha256 {got} != pinned {digest}")
    return out


def body_text(raw_html: str) -> str:
    return _WS.sub(" ", html.unescape(_TAG.sub(" ", raw_html))).strip()


def parse_posts(xml_path: Path) -> list[dict[str, object]]:
    """Questions only (PostTypeId 1): answers are not used by the intent model."""
    rows: list[dict[str, object]] = []
    for _, el in ET.iterparse(xml_path):
        if el.tag == "row" and el.get("PostTypeId") == "1":
            rows.append(
                {
                    "id": int(el.get("Id", "0")),
                    "title": (el.get("Title") or "").strip(),
                    "tags": [t for t in (el.get("Tags") or "").split("|") if t],
                    "license": el.get("ContentLicense") or "CC BY-SA 3.0",
                    "body_start": body_text(el.get("Body") or "")[:300],
                    "score": int(el.get("Score") or 0),
                }
            )
        el.clear()
    return rows


def unpack_posts(archive: Path, workdir: Path) -> Path:
    import py7zr  # training machine only

    with py7zr.SevenZipFile(archive) as z:
        z.extract(path=workdir, targets=["Posts.xml"])
    return workdir / "Posts.xml"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-dir", type=Path, help="folder that already holds the downloads")
    ap.add_argument("--keep-archives", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    src = a.from_dir or RAW
    seven = download("fitness.7z", src)
    clinc = download("clinc_data_full.json", src)
    with tempfile.TemporaryDirectory() as tmp:
        rows = parse_posts(unpack_posts(seven, Path(tmp)))
    with (RAW / "se_questions.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if clinc.parent != RAW:
        shutil.copy(clinc, RAW / clinc.name)
    if not a.keep_archives and seven.parent == RAW:
        seven.unlink()
    print(f"{len(rows)} questions -> {RAW / 'se_questions.jsonl'}")


if __name__ == "__main__":
    main()
