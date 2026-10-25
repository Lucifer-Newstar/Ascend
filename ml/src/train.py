"""train stage: data/processed -> models/food_clf.pt (+ an MLflow run).

MobileNetV3-Small from torchvision with fixed seeds. Training uses light augmentation
(random resized crop, flip, colour jitter); validation uses the exact preprocessing
contract from common.preprocess, so the val numbers match what the app will see.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

from common import (
    CROP,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MODELS_DIR,
    PROCESSED_DIR,
    REPORTS_DIR,
    TEST_OWN,
    Row,
    load_params,
    preprocess,
    read_classes,
    read_manifest,
    set_seed,
)


class OwnPhotoLeak(ValueError):
    """Raised when a team photo (test-own) shows up in a training or validation split."""


def check_no_test_own(rows: list[Row]) -> None:
    leaked = [r.path for r in rows if r.tag == TEST_OWN and r.split in ("train", "val")]
    if leaked:
        raise OwnPhotoLeak(
            f"refusing to train: {len(leaked)} test-own rows in train/val, e.g. {leaked[0]}"
        )


TRAIN_TF = transforms.Compose(
    [
        transforms.RandomResizedCrop(CROP, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(0.2, 0.2, 0.2),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN.tolist(), IMAGENET_STD.tolist()),
    ]
)


class FoodImages(Dataset[tuple[torch.Tensor, int]]):
    def __init__(self, rows: list[Row], classes: list[str], root: Path, train: bool) -> None:
        self.rows, self.root, self.train = rows, root, train
        self.index = {c: i for i, c in enumerate(classes)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        r = self.rows[i]
        img = Image.open(self.root / r.path).convert("RGB")
        x = TRAIN_TF(img) if self.train else torch.from_numpy(preprocess(img))
        return x, self.index[r.label]


def build_model(backbone: str, n_classes: int, pretrained: bool) -> nn.Module:
    if backbone != "mobilenet_v3_small":
        raise ValueError(f"unsupported backbone {backbone!r}")
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.mobilenet_v3_small(weights=weights)
    head = model.classifier[3]
    assert isinstance(head, nn.Linear)
    model.classifier[3] = nn.Linear(head.in_features, n_classes)
    return model


def recalibrate_bn(model: nn.Module, loader: DataLoader[Any]) -> None:
    """Recompute BatchNorm running statistics as an exact average over the training
    images (eval preprocessing). Cheap on small sets and removes the lag of the
    exponential running average, so validation reflects the current weights."""
    bns = [m for m in model.modules() if isinstance(m, nn.BatchNorm2d)]
    saved = [m.momentum for m in bns]
    for m in bns:
        m.reset_running_stats()
        m.momentum = None  # cumulative moving average
    model.train()
    device = next(model.parameters()).device
    with torch.no_grad():
        for x, _ in loader:
            model(x.to(device))
    for m, mom in zip(bns, saved, strict=True):
        m.momentum = mom


def evaluate(model: nn.Module, loader: DataLoader[Any]) -> tuple[float, float]:
    model.eval()
    device = next(model.parameters()).device
    correct = total = 0
    loss_sum = 0.0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x).float()
            loss_sum += nn.functional.cross_entropy(out, y, reduction="sum").item()
            correct += int((out.argmax(1) == y).sum())
            total += len(y)
    return correct / max(1, total), loss_sum / max(1, total)


def mlflow_or_none() -> Any:
    """MLflow if installed. Default store: SQLite under ml/mlruns (the file store is
    deprecated); MLFLOW_TRACKING_URI points at the compose server instead."""
    try:
        import mlflow
    except ImportError:
        return None
    import os

    from common import ML_DIR

    if not os.environ.get("MLFLOW_TRACKING_URI"):
        (ML_DIR / "mlruns").mkdir(exist_ok=True)
        mlflow.set_tracking_uri(f"sqlite:///{ML_DIR / 'mlruns' / 'mlflow.db'}")
    try:
        mlflow.set_experiment("ascend-food-cls")
    except Exception as e:  # tracking must never block a training run
        print(f"MLflow unavailable, continuing without it: {e}")
        return None
    return mlflow


def pick_device(wanted: str = "auto") -> torch.device:
    """`auto` takes the GPU when PyTorch sees one (the CUDA build on the training laptop)."""
    if wanted == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(wanted)


def train(
    params: dict[str, Any] | None = None, processed: Path = PROCESSED_DIR, out: Path = MODELS_DIR
) -> dict[str, Any]:
    params = params or load_params()
    p = params["train"]
    set_seed(params["prepare"]["seed"])
    rows = read_manifest(processed / "manifest.csv")
    check_no_test_own(rows)
    classes = read_classes(processed / "classes.json")
    g = torch.Generator().manual_seed(params["prepare"]["seed"])
    train_rows = [r for r in rows if r.split == "train"]
    val_rows = [r for r in rows if r.split == "val"]
    device = pick_device(str(p.get("device", "auto")))
    workers = int(p.get("num_workers", 0))
    # Mixed precision on the GPU halves activation memory (a 4 GB card fits batch 64).
    amp = device.type == "cuda" and bool(p.get("amp", True))
    print(f"training on {device} (amp={amp}, workers={workers})")
    tl = DataLoader(
        FoodImages(train_rows, classes, processed, True),
        batch_size=p["batch_size"],
        shuffle=True,
        generator=g,
        num_workers=workers,
        pin_memory=device.type == "cuda",
        persistent_workers=workers > 0,
    )
    vl = DataLoader(FoodImages(val_rows, classes, processed, False), batch_size=p["batch_size"])
    calib = DataLoader(
        FoodImages(train_rows, classes, processed, False), batch_size=p["batch_size"]
    )

    model = build_model(p["backbone"], len(classes), p.get("pretrained", False)).to(device)
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    opt = torch.optim.AdamW(
        model.parameters(), lr=p["lr"], weight_decay=p.get("weight_decay", 0.01)
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=p["epochs"])
    mlflow = mlflow_or_none()
    run = mlflow.start_run() if mlflow else None
    if mlflow:
        mlflow.log_params(
            {
                **{f"train.{k}": v for k, v in p.items()},
                "classes": len(classes),
                "train_rows": len(train_rows),
            }
        )

    history: list[dict[str, float]] = []
    best = (-1.0, 0)
    started = time.time()
    for epoch in range(1, p["epochs"] + 1):
        model.train()
        loss_sum, n = 0.0, 0
        for x, y in tl:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad()
            with torch.autocast(device_type=device.type, enabled=amp):
                loss = nn.functional.cross_entropy(
                    model(x), y, label_smoothing=p.get("label_smoothing", 0.0)
                )
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            loss_sum += loss.item() * len(y)
            n += len(y)
        sched.step()
        recalibrate_bn(model, calib)
        val_acc, val_loss = evaluate(model, vl)
        rec = {
            "epoch": epoch,
            "train_loss": loss_sum / max(1, n),
            "val_loss": val_loss,
            "val_acc": val_acc,
        }
        history.append(rec)
        print(json.dumps(rec))
        if mlflow:
            mlflow.log_metrics({k: v for k, v in rec.items() if k != "epoch"}, step=epoch)
        if val_acc > best[0]:
            best = (val_acc, epoch)
            out.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                    "classes": classes,
                    "backbone": p["backbone"],
                    "epoch": epoch,
                },
                out / "food_clf.pt",
            )

    summary = {
        "best_val_acc": best[0],
        "best_epoch": best[1],
        "epochs": p["epochs"],
        "seconds": round(time.time() - started, 1),
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "device": str(device),
        "run_id": run.info.run_id if run else None,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "train.json").write_text(
        json.dumps({"summary": summary, "history": history}, indent=2)
    )
    if mlflow:
        mlflow.log_metrics({"best_val_acc": best[0]})
        mlflow.log_artifact(str(processed / "classes.json"))
        mlflow.end_run()
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="train the food classifier")
    ap.add_argument("--epochs", type=int, help="override params.yaml train.epochs")
    args = ap.parse_args()
    params = load_params()
    if args.epochs:
        params["train"]["epochs"] = args.epochs
    print(json.dumps(train(params), indent=2))
