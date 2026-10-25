"""classify_intent(text) -> (intent, confidence): the trainer chat's learned router.

The model file ships inside the app (assets/intent_model.json.gz, about 0.7 MB, published
from ml/intent by `python intent/src/publish.py`). Its manifest carries the version, the
SHA-256 and the confidence threshold chosen on the eval sets. Callers use a prediction
only at or above that threshold; below it the rule router's answer stands. With the file
missing, damaged, or ASCEND_INTENT_MODEL=off, classify_intent returns None and the chat
works exactly as it did before the model existed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.modules.ml.intent_runtime import IntentModel, Prediction

log = logging.getLogger("ascend.ml")

ASSETS = Path(__file__).with_name("assets")
MODEL_FILE = ASSETS / "intent_model.json.gz"
MANIFEST_FILE = ASSETS / "intent-manifest.json"
DEFAULT_THRESHOLD = 0.55


@dataclass(frozen=True)
class IntentInfo:
    available: bool
    version: str | None
    threshold: float
    labels: list[str]
    reason: str | None  # why it is unavailable: disabled | missing | checksum | error


def _manifest() -> dict[str, Any]:
    try:
        data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _load() -> tuple[IntentModel | None, str | None]:
    # The switch is read on every call so it works without restarting the sidecar; the
    # file is read once.
    if os.environ.get("ASCEND_INTENT_MODEL", "").lower() in ("0", "off", "false"):
        return None, "disabled"
    return _load_file()


@lru_cache(maxsize=1)
def _load_file() -> tuple[IntentModel | None, str | None]:
    if not MODEL_FILE.exists():
        return None, "missing"
    expected = _manifest().get("sha256")
    if expected and hashlib.sha256(MODEL_FILE.read_bytes()).hexdigest() != expected:
        log.warning("intent model checksum mismatch; using rules only")
        return None, "checksum"
    try:
        return IntentModel.load(MODEL_FILE), None
    except (OSError, ValueError, KeyError) as e:
        log.warning("intent model failed to load (%s); using rules only", e)
        return None, "error"


def info() -> IntentInfo:
    model, reason = _load()
    return IntentInfo(
        available=model is not None,
        version=model.version if model else None,
        threshold=threshold(),
        labels=list(model.labels) if model else [],
        reason=reason,
    )


def threshold() -> float:
    try:
        return float(_manifest().get("threshold", DEFAULT_THRESHOLD))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


def predict(text: str) -> Prediction | None:
    """Full prediction (intent, confidence, top 3), or None when the model is off."""
    model, _ = _load()
    if model is None or not text.strip():
        return None
    return model.predict(text[:500])


def classify_intent(text: str) -> tuple[str, float] | None:
    """(intent, confidence) for any text, or None when the model is unavailable. The
    caller compares confidence with threshold() before trusting it."""
    p = predict(text)
    return (p.intent, p.confidence) if p is not None else None
