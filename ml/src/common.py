"""Shared pieces of the food-classifier pipeline.

The preprocessing here is the contract with the sidecar (docs/architecture/ml-pipeline.md
section 4): shorter side 256, centre crop 224 x 224, ImageNet mean/std, CHW float32.
The sidecar re-implements it without torch and both sides assert the same test vector.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

ML_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ML_DIR / "data" / "raw"
PROCESSED_DIR = ML_DIR / "data" / "processed"
MODELS_DIR = ML_DIR / "models"
REPORTS_DIR = ML_DIR / "reports"

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
RESIZE_SHORT = 256
CROP = 224

# Rows carrying this tag are the team's own photos: evaluation only, never trained on.
TEST_OWN = "test-own"


def load_params(path: Path | None = None) -> dict[str, Any]:
    with open(path or ML_DIR / "params.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def set_seed(seed: int) -> None:
    """Fix every RNG the pipeline touches so a run can be repeated exactly."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:  # the sidecar-side tests run without torch
        pass


def resize_short(img: Image.Image, short: int = RESIZE_SHORT) -> Image.Image:
    w, h = img.size
    scale = short / min(w, h)
    return img.resize((max(short, round(w * scale)), max(short, round(h * scale))), Image.BILINEAR)


def center_crop(img: Image.Image, size: int = CROP) -> Image.Image:
    w, h = img.size
    left = (w - size) // 2
    top = (h - size) // 2
    return img.crop((left, top, left + size, top + size))


def preprocess(img: Image.Image) -> np.ndarray:
    """PIL image -> normalised CHW float32 array of shape (3, 224, 224)."""
    img = center_crop(resize_short(img.convert("RGB")))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
    return np.ascontiguousarray(arr.transpose(2, 0, 1))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def average_hash(img: Image.Image, size: int = 8) -> str:
    """64-bit perceptual hash: catches the same photo re-saved or resized."""
    small = np.asarray(img.convert("L").resize((size, size), Image.BILINEAR), dtype=np.float32)
    bits = (small > small.mean()).flatten()
    return f"{int(''.join('1' if b else '0' for b in bits), 2):016x}"


@dataclass
class Row:
    path: str  # relative to data/processed
    label: str
    split: str  # train | val | test
    tag: str  # "" or test-own
    sha256: str
    source: str


MANIFEST_FIELDS = list(Row.__dataclass_fields__)


def write_manifest(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def read_manifest(path: Path | None = None) -> list[Row]:
    with open(path or PROCESSED_DIR / "manifest.csv", newline="", encoding="utf-8") as f:
        return [Row(**r) for r in csv.DictReader(f)]


def read_classes(path: Path | None = None) -> list[str]:
    with open(path or PROCESSED_DIR / "classes.json", encoding="utf-8") as f:
        return list(json.load(f))
