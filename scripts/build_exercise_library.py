"""Rebuild the bundled exercise library from free-exercise-db (needs network once).

    python scripts/build_exercise_library.py [--images]

Writes services/sidecar/app/modules/workouts/library_data/free_exercise_db.json and, with
--images, one webp per exercise, 320 px wide, into apps/desktop/public/exercises/.
free-exercise-db is released under the Unlicense (public domain); see library_data/README.md.
Needs Pillow for --images.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main"
OUT_JSON = ROOT / "services/sidecar/app/modules/workouts/library_data/free_exercise_db.json"
OUT_IMG = ROOT / "apps/desktop/public/exercises"
WIDTH = 320  # px; height follows the source aspect ratio (3:2 -> 213 px)
QUALITY = 55


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (fixed https host)
        data: bytes = r.read()
        return data


def thumbnail(ex: dict) -> None:
    from PIL import Image

    raw = fetch(f"{RAW}/exercises/{ex['images'][0]}")
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.Resampling.LANCZOS)
    im.save(OUT_IMG / f"{slugify(ex['id'])}.webp", "WEBP", quality=QUALITY, method=6)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", action="store_true", help="also rebuild the thumbnails")
    args = ap.parse_args()
    data = json.loads(fetch(f"{RAW}/dist/exercises.json"))
    trimmed = [
        {
            "id": x["id"],
            "name": x["name"],
            "category": x["category"],
            "equipment": x["equipment"],
            "force": x["force"],
            "level": x["level"],
            "mechanic": x["mechanic"],
            "primary": x["primaryMuscles"],
            "secondary": x["secondaryMuscles"],
            "instructions": [i.strip() for i in x["instructions"] if i.strip()],
            "image": f"{slugify(x['id'])}.webp" if x["images"] else None,
        }
        for x in sorted(data, key=lambda x: x["id"])
    ]
    out = {
        "source": "free-exercise-db",
        "url": "https://github.com/yuhonas/free-exercise-db",
        "license": "Unlicense (public domain dedication), see LICENSE.md in the source repository",
        "retrieved": date.today().isoformat(),
        "count": len(trimmed),
        "exercises": trimmed,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print(f"wrote {len(trimmed)} exercises to {OUT_JSON.relative_to(ROOT)}")
    if args.images:
        OUT_IMG.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(thumbnail, [x for x in data if x["images"]]))
        print(f"wrote thumbnails to {OUT_IMG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
