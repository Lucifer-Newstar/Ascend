"""How the app talks to the local model: which model, how long to wait, and why it didn't
answer. Every caller gets a reason it can show, never a silent swap.

Reasons: ai_disabled (switched off in Settings), ollama_unavailable (not running or the
model isn't pulled), timeout, model_error, guard_rejected (the reply changed or invented a
number, or tripped a banned phrase: the user never sees it).

Timeouts: the first request after the model was idle loads it into VRAM, which takes far
longer than answering (a 4 GB laptop GPU: tens of seconds), so a cold call waits up to
COLD_TIMEOUT_S; once a reply came back within the keep-alive window the normal timeout
applies. The app warms the model when the chat opens (POST /coach/warm).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import ollama
from app.modules.progress import service as progress

log = logging.getLogger("ascend.coach")

COLD_TIMEOUT_S = 60.0
WARM_WINDOW_S = 25 * 60  # inside Ollama's 30 min keep_alive
FAILURE_KEY = "ai_failures"
MODEL_KEY = "coach_model"

# (host, model) -> time.monotonic() of the last good reply.
_warm: dict[tuple[str, str], float] = {}


@dataclass(frozen=True)
class AiResult:
    text: str | None
    reason: str | None
    model: str


def model_for(db: Session, settings: Settings) -> str:
    """The model the user picked in AI setup, else the configured default."""
    return progress.get_setting(db, MODEL_KEY, "") or settings.coach_model


def is_warm(host: str, model: str) -> bool:
    t = _warm.get((host, model))
    return t is not None and time.monotonic() - t < WARM_WINDOW_S


def timeout_for(settings: Settings, model: str) -> float:
    if is_warm(settings.ollama_host, model):
        return settings.coach_timeout_s
    return max(COLD_TIMEOUT_S, settings.coach_timeout_s)


def failures(db: Session) -> int:
    return int(progress.get_setting(db, FAILURE_KEY, "0") or 0)


def _note(db: Session, ok: bool) -> None:
    progress.set_setting(db, FAILURE_KEY, "0" if ok else str(failures(db) + 1))
    db.commit()


def available(db: Session, settings: Settings) -> tuple[bool, str | None, str]:
    model = model_for(db, settings)
    if not progress.ai_enabled(db):
        return False, "ai_disabled", model
    if not ollama.is_available(settings.ollama_host, model):
        return False, "ollama_unavailable", model
    return True, None, model


def ask(
    db: Session,
    settings: Settings,
    facts: str,
    question: str,
    system: str = ollama.SYSTEM_PROMPT,
) -> AiResult:
    """One model call with a reason on every failure. The caller runs the guard."""
    ok, reason, model = available(db, settings)
    if not ok:
        return AiResult(None, reason, model)
    try:
        text = ollama.chat(
            settings.ollama_host,
            model,
            facts,
            question,
            timeout=timeout_for(settings, model),
            system=system,
        )
    except ollama.OllamaTimeout as e:
        log.info("model %s timed out: %s", model, e)
        _note(db, False)
        return AiResult(None, "timeout", model)
    except ollama.OllamaUnavailable as e:
        log.info("model %s failed: %s", model, e)
        _note(db, False)
        return AiResult(None, "model_error", model)
    _warm[(settings.ollama_host, model)] = time.monotonic()
    _note(db, True)
    return AiResult(text, None, model)


def warm(db: Session, settings: Settings) -> tuple[bool, str, float]:
    """Preload the chosen model. Returns (ok, model, seconds)."""
    ok, _, model = available(db, settings)
    if not ok:
        return False, model, 0.0
    t0 = time.monotonic()
    loaded = ollama.warm(settings.ollama_host, model)
    if loaded:
        _warm[(settings.ollama_host, model)] = time.monotonic()
    return loaded, model, round(time.monotonic() - t0, 2)
