"""Roboflow COCO export(s) -> cropped classification images for the prepare stage.

    python food/src/coco_to_cls.py --list-classes downloads/bharani
    python food/src/coco_to_cls.py downloads/bharani downloads/txofy [--out data/raw]

Each export folder is Roboflow's "COCO JSON" download: train/ valid/ test/ (any subset),
each with _annotations.coco.json beside the images. For every box whose class maps to an
ASCEND label (food/class_map.yaml, checked against labels.json) the box is cropped with
10% padding and written to

    <out>/<label>/<dataset>__<photo>__<annotation id>.jpg

<photo> is the original file name before Roboflow's "_jpg.rf.<hash>" suffix, so augmented
copies of one photo share it and prepare.py keeps them in one split. Roboflow's own
train/valid/test split is ignored on purpose: prepare.py re-splits by photo, and the gate
uses only the team's own photos. Boxes under --min-side px are skipped. A JSON report
(counts per label, skipped and unmapped classes) is written to <out>/_coco_report.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

ML = Path(__file__).resolve().parents[2]
CLASS_MAP = ML / "food" / "class_map.yaml"
LABELS = ML / "labels.json"
RAW = ML / "data" / "raw"
PAD = 0.10
SKIP = "skip"


def norm(name: str) -> str:
    return re.sub(r"[\s\-.]+", "_", name.strip().lower()).strip("_")


def photo_stem(file_name: str) -> str:
    """'idli_12_jpg.rf.8f3a.jpg' -> 'idli_12' (shared by Roboflow's augmented copies)."""
    stem = Path(file_name).name
    stem = re.sub(r"_(jpe?g|png|webp)\.rf\.[0-9a-f]+\.(jpe?g|png|webp)$", "", stem, flags=re.I)
    stem = re.sub(r"\.(jpe?g|png|webp)$", "", stem, flags=re.I)
    return re.sub(r"[^A-Za-z0-9_-]+", "-", stem)[:80]


def load_map(path: Path = CLASS_MAP, labels: Path = LABELS) -> dict[str, str]:
    aliases = {norm(k): v for k, v in yaml.safe_load(path.read_text())["aliases"].items()}
    known = set(json.loads(labels.read_text(encoding="utf-8"))["classes"])
    bad = sorted({v for v in aliases.values() if v != SKIP and v not in known})
    if bad:
        raise SystemExit(f"class_map.yaml maps to labels missing from labels.json: {bad}")
    return aliases


def annotation_files(export: Path) -> list[Path]:
    return sorted(export.glob("*/_annotations.coco.json")) + sorted(
        export.glob("_annotations.coco.json")
    )


def categories(coco: dict[str, Any]) -> dict[int, str]:
    return {int(c["id"]): str(c["name"]) for c in coco.get("categories", [])}


def crop_box(img: Image.Image, bbox: list[float], pad: float = PAD) -> Image.Image:
    x, y, w, h = bbox
    dx, dy = w * pad, h * pad
    left, top = max(0, int(x - dx)), max(0, int(y - dy))
    right, bottom = min(img.width, int(x + w + dx)), min(img.height, int(y + h + dy))
    return img.crop((left, top, right, bottom))


@dataclass
class Report:
    written: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    unmapped: Counter[str] = field(default_factory=Counter)
    too_small: int = 0
    missing_images: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "written": dict(sorted(self.written.items())),
            "total": sum(self.written.values()),
            "skipped_classes": dict(self.skipped),
            "unmapped_classes": dict(self.unmapped.most_common()),
            "too_small": self.too_small,
            "missing_images": self.missing_images,
        }


def convert(exports: list[Path], out: Path, aliases: dict[str, str], min_side: int = 64) -> Report:
    rep = Report()
    for export in exports:
        dataset = norm(export.name)
        for ann_file in annotation_files(export):
            coco = json.loads(ann_file.read_text(encoding="utf-8"))
            cats = categories(coco)
            images = {int(i["id"]): i for i in coco.get("images", [])}
            by_image: dict[int, list[dict[str, Any]]] = {}
            for a in coco.get("annotations", []):
                by_image.setdefault(int(a["image_id"]), []).append(a)
            for image_id, anns in sorted(by_image.items()):
                info = images.get(image_id)
                path = ann_file.parent / str(info["file_name"]) if info else None
                if path is None or not path.exists():
                    rep.missing_images += 1
                    continue
                with Image.open(path) as im:
                    img = im.convert("RGB")
                for a in anns:
                    name = cats.get(int(a["category_id"]), "?")
                    label = aliases.get(norm(name))
                    if label is None:
                        rep.unmapped[name] += 1
                        continue
                    if label == SKIP:
                        rep.skipped[name] += 1
                        continue
                    crop = crop_box(img, [float(v) for v in a["bbox"]])
                    if min(crop.size) < min_side:
                        rep.too_small += 1
                        continue
                    dest = (
                        out / label / f"{dataset}__{photo_stem(info['file_name'])}__{a['id']}.jpg"
                    )
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    crop.save(dest, quality=92)
                    rep.written[label] += 1
    return rep


def list_classes(exports: list[Path]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for export in exports:
        for ann_file in annotation_files(export):
            coco = json.loads(ann_file.read_text(encoding="utf-8"))
            cats = categories(coco)
            counts.update(cats.get(int(a["category_id"]), "?") for a in coco.get("annotations", []))
    return dict(counts.most_common())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("exports", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=RAW)
    ap.add_argument("--min-side", type=int, default=64)
    ap.add_argument("--list-classes", action="store_true", help="print class names and box counts")
    a = ap.parse_args()
    if a.list_classes:
        aliases = load_map()
        for name, n in list_classes(a.exports).items():
            print(f"{n:6d}  {name!r:32} -> {aliases.get(norm(name), 'UNMAPPED')}")
        return 0
    rep = convert(a.exports, a.out, load_map(), a.min_side)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "_coco_report.json").write_text(json.dumps(rep.as_dict(), indent=2))
    print(json.dumps(rep.as_dict(), indent=2))
    return 0 if rep.written else 1


if __name__ == "__main__":
    sys.exit(main())
