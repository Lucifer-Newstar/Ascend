"""export stage: models/food_clf.pt -> models/food_clf.onnx + models-manifest.json.

The ONNX graph is checked against PyTorch on up to 200 processed images (parity gate:
identical top-1 and max softmax difference under 1e-4) before the manifest is written.
The manifest is what the sidecar reads: file name, SHA-256, classes, input contract.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from common import (
    CROP,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MODELS_DIR,
    PROCESSED_DIR,
    preprocess,
    read_manifest,
    sha256_file,
)
from evaluate import softmax
from train import build_model

OPSET = 17
PARITY_ATOL = 1e-4
MODEL_NAME = "ascend-food-cls"


class ParityError(RuntimeError):
    pass


def parity(onnx_path: Path, model: torch.nn.Module, images: list[np.ndarray]) -> dict[str, Any]:
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    max_diff, agree = 0.0, 0
    for i in range(0, len(images), 32):
        batch = np.stack(images[i : i + 32])
        with torch.no_grad():
            ref = softmax(model(torch.from_numpy(batch)).numpy())
        got = softmax(sess.run(None, {"input": batch})[0])
        max_diff = max(max_diff, float(np.abs(ref - got).max()))
        agree += int((ref.argmax(1) == got.argmax(1)).sum())
    result = {
        "images": len(images),
        "max_softmax_diff": max_diff,
        "top1_agreement": agree / max(1, len(images)),
    }
    if max_diff > PARITY_ATOL or agree != len(images):
        raise ParityError(f"ONNX parity failed: {result}")
    return result


def export(
    models_dir: Path = MODELS_DIR, processed: Path = PROCESSED_DIR, version: str = "0.0.0-smoke"
) -> dict:
    ckpt = torch.load(models_dir / "food_clf.pt", map_location="cpu", weights_only=False)
    classes: list[str] = ckpt["classes"]
    model = build_model(ckpt["backbone"], len(classes), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    onnx_path = models_dir / "food_clf.onnx"
    torch.onnx.export(
        model,
        (torch.zeros(1, 3, CROP, CROP),),
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=OPSET,
        dynamo=False,
    )
    import onnx

    onnx.checker.check_model(str(onnx_path))

    rows = [r for r in read_manifest(processed / "manifest.csv") if r.split in ("test", "val")][
        :200
    ]
    check = parity(onnx_path, model, [preprocess(Image.open(processed / r.path)) for r in rows])

    manifest = {
        "name": MODEL_NAME,
        "version": version,
        "file": onnx_path.name,
        "sha256": sha256_file(onnx_path),
        "bytes": onnx_path.stat().st_size,
        "backbone": ckpt["backbone"],
        "epoch": ckpt["epoch"],
        "classes": classes,
        "input": {"name": "input", "shape": ["batch", 3, CROP, CROP], "dtype": "float32"},
        "output": {"name": "logits", "shape": ["batch", len(classes)]},
        "preprocessing": {
            "resize_short": 256,
            "center_crop": CROP,
            "mean": IMAGENET_MEAN.round(3).tolist(),
            "std": IMAGENET_STD.round(3).tolist(),
            "layout": "CHW",
        },
        "opset": OPSET,
        "parity": check,
        "min_app_version": "0.2.0",
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (models_dir / "models-manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    from common import load_params

    m = export(version=load_params().get("export", {}).get("version", "0.0.0-smoke"))
    print(json.dumps({k: m[k] for k in ("file", "sha256", "bytes", "classes", "parity")}, indent=2))
