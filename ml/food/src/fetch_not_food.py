"""Open Images V7 photos with NO food in them -> data/raw/not_food/ (the reject class).

    python food/src/fetch_not_food.py --limit 1500 [--out data/raw/not_food] [--clean]

Uses the validation split's human-verified image labels (a 28 MB CSV) and picks photos
that carry at least one everyday-scene label (people, rooms, desks, vehicles, pets, empty
tableware...) and none of the food labels below. Photos are fetched from the public Open
Images bucket, resized to a 512 px short side, and listed with author, licence and source
URL in _ATTRIBUTION.csv beside them.

Licences: Open Images annotations are CC BY 4.0 (Google). The photos are Flickr uploads
that Open Images lists as CC BY 2.0; keep _ATTRIBUTION.csv with any copy of the data.
The CSVs (about 44 MB) are cached in food/.cache and removed with --clean.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import requests
from PIL import Image

ML = Path(__file__).resolve().parents[2]
OUT = ML / "data" / "raw" / "not_food"
CACHE = ML / "food" / ".cache"
BASE = "https://storage.googleapis.com/openimages"
CSVS = {
    "labels": f"{BASE}/v7/oidv7-val-annotations-human-imagelabels.csv",
    "classes": f"{BASE}/v7/oidv7-class-descriptions.csv",
    "images": f"{BASE}/2018_04/validation/validation-images-with-rotation.csv",
}
IMAGE_URL = "https://s3.amazonaws.com/open-images-dataset/validation/{id}.jpg"

# Positive labels a not-food photo may carry (what a phone camera sees around a meal).
SCENES = [
    "Person",
    "Human face",
    "Hand",
    "Room",
    "Table",
    "Desk",
    "Chair",
    "Couch",
    "Bed",
    "Kitchen",
    "Countertop",
    "Tableware",
    "Plate",
    "Bowl",
    "Mug",
    "Laptop",
    "Computer keyboard",
    "Mobile phone",
    "Book",
    "Car",
    "Bicycle",
    "Street",
    "Building",
    "Tree",
    "Dog",
    "Cat",
    "Shoe",
    "Clothing",
    "Bag",
    "Window",
    "Door",
    "Flower",
    "Toy",
    "Television",
]
# Any of these (or a label whose name contains one of the words) disqualifies a photo.
FOOD_WORDS = [
    "food",
    "fruit",
    "vegetable",
    "dish",
    "cuisine",
    "meal",
    "snack",
    "dessert",
    "baked",
    "bread",
    "drink",
    "beverage",
    "juice",
    "coffee",
    "tea",
    "cake",
    "cookie",
    "pizza",
    "burger",
    "sandwich",
    "salad",
    "soup",
    "noodle",
    "pasta",
    "rice",
    "egg",
    "meat",
    "fish",
    "seafood",
    "cheese",
    "milk",
    "banana",
    "apple",
    "orange",
    "lemon",
    "tomato",
    "potato",
    "candy",
    "chocolate",
    "ice cream",
    "wine",
    "beer",
    "cocktail",
    "breakfast",
    "lunch",
    "dinner",
    "fast food",
    "produce",
    "ingredient",
    "recipe",
    "taco",
    "sushi",
    "doughnut",
]


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def is_food(name: str) -> bool:
    n = name.lower()
    return any(w in n for w in FOOD_WORDS)


def pick(
    label_rows: list[dict[str, str]],
    names: dict[str, str],
    limit: int,
    seed: int = 42,
) -> list[tuple[str, str]]:
    """(image id, scene label) pairs, balanced over SCENES, for photos with no food label."""
    positives: dict[str, set[str]] = defaultdict(set)
    for r in label_rows:
        if r.get("Confidence", "1") in ("1", "1.0"):
            positives[r["ImageID"]].add(names.get(r["LabelName"], r["LabelName"]))
    by_scene: dict[str, list[str]] = defaultdict(list)
    for image_id, labels in sorted(positives.items()):
        if any(is_food(x) for x in labels):
            continue
        for scene in SCENES:
            if scene in labels:
                by_scene[scene].append(image_id)
    rng = random.Random(seed)
    for ids in by_scene.values():
        rng.shuffle(ids)
    chosen: list[tuple[str, str]] = []
    seen: set[str] = set()
    while len(chosen) < limit and any(by_scene.values()):
        for scene in SCENES:
            ids = by_scene.get(scene, [])
            while ids and ids[-1] in seen:
                ids.pop()
            if ids and len(chosen) < limit:
                image_id = ids.pop()
                seen.add(image_id)
                chosen.append((image_id, scene))
    return chosen


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch(limit: int, out: Path, seed: int = 42) -> int:
    paths = {k: download(u, CACHE / Path(u).name) for k, u in CSVS.items()}
    with open(paths["classes"], newline="", encoding="utf-8") as f:
        names = {row[0]: row[1] for row in csv.reader(f) if len(row) >= 2}
    chosen = pick(read_csv(paths["labels"]), names, limit, seed)
    meta = {r["ImageID"]: r for r in read_csv(paths["images"])}
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out / "_ATTRIBUTION.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "image_id", "scene", "author", "license", "original_url"])
        for image_id, scene in chosen:
            dest = out / f"openimages__{image_id}__0.jpg"
            if not dest.exists():
                try:
                    r = requests.get(IMAGE_URL.format(id=image_id), timeout=30)
                    r.raise_for_status()
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                except (requests.RequestException, OSError) as e:
                    print(f"skip {image_id}: {e}", file=sys.stderr)
                    continue
                scale = 512 / min(img.size)
                if scale < 1:
                    img = img.resize((round(img.width * scale), round(img.height * scale)))
                img.save(dest, quality=90)
            m = meta.get(image_id, {})
            w.writerow(
                [
                    dest.name,
                    image_id,
                    scene,
                    m.get("Author", ""),
                    m.get("License", ""),
                    m.get("OriginalURL", ""),
                ]
            )
            written += 1
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--limit", type=int, default=1500)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--clean", action="store_true", help="delete the cached CSVs afterwards")
    a = ap.parse_args()
    n = fetch(a.limit, a.out, a.seed)
    print(f"wrote {n} not-food photos to {a.out}")
    if a.clean:
        shutil.rmtree(CACHE, ignore_errors=True)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
