"""Generate a tiny synthetic image set so the whole pipeline can run anywhere.

These are NOT food photos: each "class" is a distinct colour and shape pattern with
noise, jitter and random backgrounds. They exist so CI and a fresh clone can exercise
prepare -> train -> export -> evaluate end to end in a couple of minutes on a CPU.
Real datasets are pulled with DVC (see ml/README.md) and never generated.

    python src/make_smoke_data.py --classes 4 --per-class 40 --own 6
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import RAW_DIR, TEST_OWN

# Class names borrow real label ids so labels.json lookups are exercised, but the
# pixels are synthetic patterns (see module docstring).
SMOKE_CLASSES = ["idli", "dosa", "sambar", "chapati", "rice", "dal"]
PALETTE = [
    (240, 236, 220),
    (196, 140, 60),
    (170, 80, 30),
    (210, 170, 110),
    (250, 250, 245),
    (230, 180, 40),
]
SHAPES = ["circle", "triangle", "bowl", "disc", "grain", "ring"]


def draw_sample(cls_idx: int, rng: random.Random, size: int = 288) -> Image.Image:
    bg = tuple(rng.randint(20, 90) for _ in range(3))
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    colour = tuple(max(0, min(255, c + rng.randint(-25, 25))) for c in PALETTE[cls_idx])
    cx, cy = size // 2 + rng.randint(-30, 30), size // 2 + rng.randint(-30, 30)
    r = rng.randint(70, 110)
    shape = SHAPES[cls_idx]
    if shape == "circle":
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour)
    elif shape == "triangle":
        d.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], fill=colour)
    elif shape == "bowl":
        d.pieslice((cx - r, cy - r, cx + r, cy + r), 0, 180, fill=colour)
    elif shape == "disc":
        d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), fill=colour)
    elif shape == "grain":
        for _ in range(60):
            x, y = cx + rng.randint(-r, r), cy + rng.randint(-r, r)
            d.ellipse((x - 6, y - 3, x + 6, y + 3), fill=colour)
    else:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=colour, width=22)
    arr = np.asarray(img, dtype=np.int16)
    noise = np.random.default_rng(rng.randint(0, 2**31)).integers(-18, 18, arr.shape)
    img = Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))
    return img.filter(ImageFilter.GaussianBlur(rng.uniform(0, 1.2))).rotate(rng.uniform(-20, 20))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--classes", type=int, default=4)
    ap.add_argument("--per-class", type=int, default=40)
    ap.add_argument("--own", type=int, default=6, help="'team photo' samples per class (test-own)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=RAW_DIR)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    if args.out.exists():
        shutil.rmtree(args.out)
    for i, name in enumerate(SMOKE_CLASSES[: args.classes]):
        for kind, n in (("", args.per_class), (TEST_OWN, args.own)):
            folder = args.out / f"_{TEST_OWN}" / name if kind else args.out / name
            folder.mkdir(parents=True, exist_ok=True)
            for j in range(n):
                draw_sample(i, rng).save(folder / f"{name}_{kind or 'src'}_{j:03d}.png")
    # One exact duplicate and one resized near-duplicate, so dedupe has work to do.
    first = args.out / SMOKE_CLASSES[0]
    src = sorted(first.glob("*.png"))[0]
    shutil.copy(src, first / "dup_exact.png")
    Image.open(src).resize((200, 200)).save(first / "dup_resized.png")
    print(f"wrote synthetic smoke set to {args.out}")


if __name__ == "__main__":
    main()
