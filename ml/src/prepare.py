"""prepare stage: data/raw -> data/processed.

Layout read:   data/raw/<label>/*.jpg|png          (training sources)
               data/raw/_test-own/<label>/*        (team photos: test split only)
Written:       data/processed/images/<sha>.png      (shorter side 256, RGB)
               data/processed/manifest.csv          (path, label, split, tag, sha256, source)
               data/processed/classes.json          (index -> label, sorted)
               data/processed/prepare_report.json   (counts and what was dropped)

Steps: exact dedupe by sha256, near-dedupe by average hash, stratified split with a
fixed seed. Team photos never reach train or val (ml-pipeline.md section 3).
"""

from __future__ import annotations

import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from common import (
    PROCESSED_DIR,
    RAW_DIR,
    TEST_OWN,
    Row,
    average_hash,
    load_params,
    resize_short,
    sha256_file,
    write_manifest,
)

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def images_in(folder: Path) -> list[Path]:
    return [f for f in sorted(folder.iterdir()) if f.suffix.lower() in EXTS]


def collect(raw: Path) -> list[tuple[Path, str, str]]:
    """(file, label, tag) for every image under raw/."""
    items: list[tuple[Path, str, str]] = []
    for label_dir in sorted(p for p in raw.iterdir() if p.is_dir()):
        if label_dir.name == f"_{TEST_OWN}":
            for own in sorted(p for p in label_dir.iterdir() if p.is_dir()):
                items += [(f, own.name, TEST_OWN) for f in images_in(own)]
        elif not label_dir.name.startswith("_"):
            items += [(f, label_dir.name, "") for f in images_in(label_dir)]
    return items


def split_rows(rows: list[Row], val: float, test: float, seed: int) -> None:
    """Stratified split in place; test-own rows are fixed to test."""
    by_label: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        if r.tag == TEST_OWN:
            r.split = "test"
        else:
            by_label[r.label].append(r)
    rng = random.Random(seed)
    for label in sorted(by_label):
        group = sorted(by_label[label], key=lambda r: r.sha256)
        rng.shuffle(group)
        n_val = max(1, round(len(group) * val)) if len(group) >= 3 else 0
        n_test = max(1, round(len(group) * test)) if len(group) >= 3 else 0
        for i, r in enumerate(group):
            r.split = "val" if i < n_val else "test" if i < n_val + n_test else "train"


def prepare(raw: Path = RAW_DIR, out: Path = PROCESSED_DIR, params: dict | None = None) -> dict:
    p = (params or load_params())["prepare"]
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)

    seen_sha: set[str] = set()
    seen_ahash: dict[str, str] = {}
    dropped: Counter[str] = Counter()
    rows: list[Row] = []
    for f, label, tag in collect(raw):
        sha = sha256_file(f)
        if sha in seen_sha:
            dropped["exact_duplicate"] += 1
            continue
        try:
            img = Image.open(f).convert("RGB")
        except (UnidentifiedImageError, OSError):
            dropped["unreadable"] += 1
            continue
        if min(img.size) < p.get("min_side", 64):
            dropped["too_small"] += 1
            continue
        ahash = average_hash(img, size=16)
        if ahash in seen_ahash and seen_ahash[ahash] == label:
            dropped["near_duplicate"] += 1
            continue
        seen_sha.add(sha)
        seen_ahash[ahash] = label
        name = f"images/{sha[:16]}.png"
        resize_short(img).save(out / name)
        rows.append(Row(name, label, "", tag, sha, str(f.relative_to(raw))))

    split_rows(rows, p["val_split"], p["test_split"], p["seed"])
    rows.sort(key=lambda r: (r.split, r.label, r.sha256))
    write_manifest(rows, out / "manifest.csv")
    classes = sorted({r.label for r in rows})
    (out / "classes.json").write_text(json.dumps(classes, indent=2))
    report = {
        "images": len(rows),
        "classes": len(classes),
        "per_split": dict(Counter(r.split for r in rows)),
        "test_own": sum(r.tag == TEST_OWN for r in rows),
        "dropped": dict(dropped),
    }
    (out / "prepare_report.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
