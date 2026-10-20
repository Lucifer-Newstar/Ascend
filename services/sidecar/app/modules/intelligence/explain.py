"""Plain-language explanations of engine numbers (ADR-0016).

The engines decide every number; this module only phrases. The template text is always
available and is what the user sees unless all of these hold: AI is on, the local model
answers in time, and the coach guard (coach/validate.py: number fidelity V3, banned
phrases V4) passes the model's sentence against the facts block. Any failure falls back
to the template, and the response says which text was shown and why.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.coach import ollama, validate
from app.modules.intelligence import progression as prog
from app.modules.intelligence import recovery as rec
from app.modules.progress import service as progress

log = logging.getLogger(__name__)
EXPLAIN_VERSION = "explain-v1"
SYSTEM_PROMPT = (
    "You rewrite one explanation from a fitness app's own formulas for the lifter. "
    "Write ONE short sentence (at most 30 words), plain and friendly. Use ONLY numbers "
    "that appear in the facts; never add, change or round a number. No medical advice."
)
CACHE_SIZE = 256


@dataclass(frozen=True)
class Explanation:
    text: str
    template: str
    phrasing: str  # "model" | "template"
    model: str | None
    fallback: str | None  # why the template was shown, None when the model text was used
    checks: dict[str, str] | None
    facts: str
    version: str = EXPLAIN_VERSION


_cache: OrderedDict[tuple[str, str, str], Explanation] = OrderedDict()


def clear_cache() -> None:
    _cache.clear()


def _fmt(v: float | int | str) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def facts_block(facts: dict[str, float | int | str], template: str) -> str:
    lines = [f"- {k.replace('_', ' ')}: {_fmt(v)}" for k, v in sorted(facts.items())]
    return "\n".join(lines + [f"- explanation: {template}"])


def target_facts(t: prog.Target) -> dict[str, float | int | str]:
    f = dict(t.facts)
    f["sets"] = t.sets
    if t.reps is not None:
        f["target_reps"] = t.reps
    if t.seconds is not None:
        f["target_seconds"] = t.seconds
    if t.weight_kg:
        f["target_load_kg"] = t.weight_kg
    if t.rpe is not None:
        f["target_rpe"] = t.rpe
    if t.e1rm and t.e1rm.current is not None:
        f["e1rm_now"] = t.e1rm.current
    return f


def muscle_template(m: rec.MuscleRecovery) -> tuple[str, dict[str, float | int | str]]:
    pct = round(m.readiness * 100)
    facts: dict[str, float | int | str] = {
        "readiness_pct": pct,
        "population_readiness_pct": round(m.readiness_population * 100),
        "fatigue_effective_sets": round(m.fatigue, 1),
        "capacity_effective_sets": m.capacity,
        "half_life_h": m.half_life_h,
        "personal_factor_k": m.k,
        "checkin_modifier": m.modifier,
    }
    if m.last_trained is None:
        return f"{m.label} has no recent training, so it is fully recovered.", facts
    text = (
        f"{m.label} is {pct}% ready: {round(m.fatigue, 1)} effective sets of fatigue left "
        f"against a capacity of {_fmt(m.capacity)}, fading with a "
        f"{_fmt(m.half_life_h)} h half-life."
    )
    if abs(m.k - 1.0) > 1e-9:
        text += f" The population would be {round(m.readiness_population * 100)}%."
    if m.modifier > 1:
        text += f" Today's check-in multiplies fatigue by {_fmt(m.modifier)}."
    return text, facts


def explain(
    db: Session,
    settings: Settings,
    key: tuple[str, str, str],
    template: str,
    facts: dict[str, float | int | str],
) -> Explanation:
    """`key` identifies the explained number (kind, subject, value) for the cache."""
    block = facts_block(facts, template)
    if not progress.ai_enabled(db):
        return Explanation(template, template, "template", None, "ai_disabled", None, block)
    cached = _cache.get(key)
    if cached is not None and cached.template == template:
        _cache.move_to_end(key)
        return cached
    if not ollama.is_available(settings.ollama_host, settings.coach_model):
        return Explanation(template, template, "template", None, "model_unavailable", None, block)
    try:
        text = ollama.chat(
            settings.ollama_host,
            settings.coach_model,
            block,
            f"Rewrite the explanation for the lifter: {template}",
            timeout=settings.coach_timeout_s,
            system=SYSTEM_PROMPT,
        )
    except ollama.OllamaUnavailable as e:
        return Explanation(
            template,
            template,
            "template",
            settings.coach_model,
            f"model_error: {e}"[:120],
            None,
            block,
        )
    checks = validate.check_reply(text, block, None)
    if not checks.ok:
        failed = "numbers" if not checks.numbers.ok else "banned"
        log.info("explanation replaced: %s check failed", failed)
        out = Explanation(
            template,
            template,
            "template",
            settings.coach_model,
            f"check_failed: {failed}",
            checks.summary(),
            block,
        )
    else:
        out = Explanation(
            text, template, "model", settings.coach_model, None, checks.summary(), block
        )
    _cache[key] = out
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return out
