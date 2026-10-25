"""Food photo suggestions (food-photo v0): ONNX Runtime on the CPU, never auto-logging.

The model is NOT bundled. It is trained on the team's GPU (ml/, see ml/food/README.md),
published with its model card, and placed in <data dir>/models/food/ as
  food_clf.onnx + models-manifest.json   (written by ml/src/export_onnx.py)
The feature exists only when all of these hold, otherwise status() says why and the UI
hides "Scan meal":
  * the manifest's gate says passed (a model evaluated on the team's own photos),
  * the ONNX file matches the manifest's SHA-256,
  * onnxruntime, numpy and Pillow import (the sidecar's dependencies),
  * the user has not switched it off (setting food_scan_enabled = "false").

suggest() returns the top 3 foods with confidences for the user to CONFIRM. The caller
never logs a meal from it; logging stays the normal meal flow after the user picks.
Preprocessing is the contract in ml/src/common.py: shorter side 256, centre crop 224,
ImageNet mean/std, CHW float32.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger("ascend.ml")

SETTING_KEY = "food_scan_enabled"
MODEL_SUBDIR = Path("models") / "food"
MANIFEST = "models-manifest.json"
NOT_FOOD = "not_food"
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
RESIZE_SHORT = 256
CROP = 224


class FoodPhotoError(Exception):
    """The photo could not be read (not an image, too small)."""


@dataclass(frozen=True)
class Status:
    available: bool
    reason: str | None  # missing | not_gated | checksum | runtime_missing | disabled | error
    version: str | None
    classes: int
    model_dir: str


@dataclass(frozen=True)
class Guess:
    label: str
    food_name: str | None
    confidence: float


def model_dir(data_dir: Path) -> Path:
    env = os.environ.get("ASCEND_FOOD_MODEL_DIR")
    return Path(env) if env else data_dir / MODEL_SUBDIR


def _manifest(folder: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


_sessions: dict[tuple[str, str], Any] = {}


def _runtime() -> Any | None:
    try:
        import numpy  # noqa: F401
        import onnxruntime
        from PIL import Image  # noqa: F401
    except ImportError:
        return None
    return onnxruntime


def status(data_dir: Path, enabled: bool = True) -> Status:
    folder = model_dir(data_dir)
    m = _manifest(folder)
    version = str(m.get("version")) if m else None
    classes = len(m.get("classes", [])) if m else 0

    def out(ok: bool, reason: str | None) -> Status:
        return Status(ok, reason, version, classes, str(folder))

    if not enabled:
        return out(False, "disabled")
    if m is None or not (folder / str(m.get("file", ""))).is_file():
        return out(False, "missing")
    if not (m.get("gate") or {}).get("passed"):
        # Viva rule: the app never claims to recognise food without a model that passed the
        # gate on the team's own photos.
        return out(False, "not_gated")
    path = folder / str(m["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != m.get("sha256"):
        return out(False, "checksum")
    if _runtime() is None:
        return out(False, "runtime_missing")
    return out(True, None)


def preprocess(raw: bytes) -> Any:
    """Image bytes -> float32 array (1, 3, 224, 224), the training contract."""
    import numpy as np
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        img: Image.Image = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        raise FoodPhotoError("that file is not a photo ASCEND can read") from e
    w, h = img.size
    if min(w, h) < 64:
        raise FoodPhotoError("the photo is too small; use at least 64 px on the short side")
    scale = RESIZE_SHORT / min(w, h)
    img = img.resize(
        (max(CROP, round(w * scale)), max(CROP, round(h * scale))), Image.Resampling.BILINEAR
    )
    w, h = img.size
    left, top = (w - CROP) // 2, (h - CROP) // 2
    img = img.crop((left, top, left + CROP, top + CROP))
    pixels = np.asarray(img, dtype=np.float32) / 255.0
    norm = (pixels - np.array(MEAN, dtype=np.float32)) / np.array(STD, dtype=np.float32)
    return norm.transpose(2, 0, 1)[None, ...].astype(np.float32)


def _session(folder: Path, m: dict[str, Any]) -> Any:
    key = (str(folder), str(m.get("sha256")))
    if key not in _sessions:
        ort = _runtime()
        assert ort is not None
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2  # a laptop CPU shared with the UI
        _sessions[key] = ort.InferenceSession(
            str(folder / str(m["file"])), sess_options=opts, providers=["CPUExecutionProvider"]
        )
    return _sessions[key]


def suggest(data_dir: Path, raw: bytes, k: int = 3) -> tuple[list[Guess], str]:
    """Top-k guesses (best first) and the model version. Call status() first."""
    folder = model_dir(data_dir)
    m = _manifest(folder)
    assert m is not None
    sess = _session(folder, m)
    x = preprocess(raw)
    name = sess.get_inputs()[0].name
    logits = [float(v) for v in sess.run(None, {name: x})[0][0]]
    top = max(logits)
    exps = [math.exp(v - top) for v in logits]
    total = sum(exps)
    probs = [e / total for e in exps]
    classes: list[str] = list(m.get("classes", []))
    names: dict[str, str] = dict(m.get("food_names", {}))
    order = sorted(range(len(probs)), key=lambda i: -probs[i])[:k]
    guesses = [
        Guess(classes[i], names.get(classes[i]), round(probs[i], 4))
        for i in order
        if i < len(classes)
    ]
    return guesses, str(m.get("version"))
