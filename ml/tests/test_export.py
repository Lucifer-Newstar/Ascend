from __future__ import annotations

import json
import random
from pathlib import Path

import torch

from common import TEST_OWN
from export_onnx import export
from make_smoke_data import draw_sample
from prepare import prepare
from train import build_model


def test_export_writes_manifest_and_passes_parity(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    rng = random.Random(5)
    for i, label in enumerate(["idli", "dosa"]):
        (raw / label).mkdir(parents=True)
        (raw / f"_{TEST_OWN}" / label).mkdir(parents=True)
        for j in range(6):
            draw_sample(i, rng).save(raw / label / f"{j}.png")
        draw_sample(i, rng).save(raw / f"_{TEST_OWN}" / label / "own.png")
    processed = tmp_path / "processed"
    prepare(raw, processed, {"prepare": {"val_split": 0.2, "test_split": 0.2, "seed": 1}})

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    model = build_model("mobilenet_v3_small", 2, pretrained=False).eval()
    ckpt = {
        "state_dict": model.state_dict(),
        "classes": ["dosa", "idli"],
        "backbone": "mobilenet_v3_small",
        "epoch": 0,
    }
    torch.save(ckpt, models_dir / "food_clf.pt")

    m = export(models_dir, processed, version="0.0.0-test")
    assert m["parity"]["top1_agreement"] == 1.0
    assert m["parity"]["max_softmax_diff"] < 1e-4
    assert m["classes"] == ["dosa", "idli"]
    on_disk = json.loads((models_dir / "models-manifest.json").read_text())
    assert on_disk["sha256"] == m["sha256"] and len(m["sha256"]) == 64
