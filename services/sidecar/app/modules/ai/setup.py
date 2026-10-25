"""ai-tiers-v1: which model this PC should run, if any.

Tier 0 (rules) is the whole app without a model: chat routing and help notes, tours,
rule-based plans and checks, action cards, template captions. A model only adds free-form
wording. Sizes are Ollama's
published download sizes (ollama.com/library/qwen3, read 2026-10-23).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.ai import hardware
from app.modules.coach import ollama, runtime
from app.modules.progress import service as progress

TIERS_VERSION = "ai-tiers-v1"

# Text models ASCEND recommends, largest first: (tag, download GB, minimum VRAM GB, RAM GB).
MODELS: tuple[tuple[str, float, float, float], ...] = (
    ("qwen3:4b", 2.5, 4.0, 16.0),
    ("qwen3:1.7b", 1.4, 2.0, 8.0),
    ("qwen3:0.6b", 0.5, 0.0, 4.0),
)
SIZE_GB = {tag: gb for tag, gb, _, _ in MODELS}
FAILURES_BEFORE_SUGGESTION = 3


@dataclass(frozen=True)
class Recommendation:
    model: str | None  # None: stay on rules
    reason: str


def recommend(ram_gb: float | None, vram_gb: float | None) -> Recommendation:
    if vram_gb is not None and vram_gb >= 4:
        return Recommendation(
            "qwen3:4b", f"{vram_gb:g} GB of graphics memory runs qwen3:4b (2.5 GB) on the GPU."
        )
    if vram_gb is not None and vram_gb >= 2:
        return Recommendation(
            "qwen3:1.7b", f"{vram_gb:g} GB of graphics memory fits qwen3:1.7b (1.4 GB)."
        )
    if ram_gb is not None and ram_gb >= 16:
        return Recommendation(
            "qwen3:1.7b", f"No large GPU found; {ram_gb:g} GB of RAM runs qwen3:1.7b on the CPU."
        )
    if ram_gb is not None and ram_gb >= 8:
        return Recommendation(
            "qwen3:0.6b",
            f"No large GPU found and {ram_gb:g} GB of RAM: the small qwen3:0.6b (0.5 GB) keeps "
            f"replies quick.",
        )
    if ram_gb is None:
        return Recommendation(
            "qwen3:0.6b", "Couldn't read this PC's memory; the small model is the safe start."
        )
    return Recommendation(
        None, f"{ram_gb:g} GB of RAM is tight for a local model; the rule-based mode is best."
    )


def smaller_than(model: str) -> str | None:
    tags = [t for t, _, _, _ in MODELS]
    if model not in tags:
        return tags[-1]
    i = tags.index(model)
    return tags[i + 1] if i + 1 < len(tags) else None


def setup(db: Session, settings: Settings) -> dict[str, object]:
    hw = hardware.detect()
    version, installed = ollama.server_info(settings.ollama_host)
    names = {n for n, _ in installed}
    model = runtime.model_for(db, settings)
    rec = recommend(hw.ram_gb, hw.vram_gb)
    fails = runtime.failures(db)
    suggestion = None
    if fails >= FAILURES_BEFORE_SUGGESTION:
        smaller = smaller_than(model)
        suggestion = (
            f"The last {fails} AI answers failed or timed out. Switch to {smaller}"
            if smaller
            else f"The last {fails} AI answers failed or timed out. Switch to rule-based mode"
        )
        suggestion += " for quicker answers?"

    def has(m: str) -> bool:
        return m in names or f"{m}:latest" in names

    ai_on = progress.ai_enabled(db)
    ready = ai_on and version is not None and has(model)
    return {
        "ai_enabled": ai_on,
        "tier": "ai" if ready else "rules",
        "ollama_installed": version is not None or hardware.ollama_installed(),
        "ollama_running": version is not None,
        "ollama_version": version,
        "models": [{"name": n, "size_gb": round(b / 1e9, 1)} for n, b in installed],
        "model": model,
        "model_installed": has(model),
        "recommended": {
            "model": rec.model,
            "size_gb": SIZE_GB.get(rec.model) if rec.model else None,
            "reason": rec.reason,
            "pull_command": f"ollama pull {rec.model}" if rec.model else None,
        },
        "hardware": {"ram_gb": hw.ram_gb, "vram_gb": hw.vram_gb, "gpu": hw.gpu},
        "failures": fails,
        "suggestion": suggestion,
        "smaller_model": smaller_than(model),
        "algo_version": TIERS_VERSION,
    }


def choose(db: Session, model: str | None) -> None:
    """Remember the user's model (None: back to the default) and reset the failure count."""
    progress.set_setting(db, runtime.MODEL_KEY, model or "")
    progress.set_setting(db, runtime.FAILURE_KEY, "0")
    db.commit()


def run_test(db: Session, settings: Settings) -> dict[str, object]:
    import time

    t0 = time.monotonic()
    r = runtime.ask(
        db, settings, "The user is testing the local AI.", "Reply with one short friendly sentence."
    )
    return {
        "ok": r.text is not None,
        "model": r.model,
        "seconds": round(time.monotonic() - t0, 2),
        "reason": r.reason,
        "reply": (r.text or "")[:200],
    }
