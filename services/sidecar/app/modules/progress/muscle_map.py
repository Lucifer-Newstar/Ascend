"""Detailed muscle mapping (muscle-map-v1, docs/research/v8-exercise-muscle-mapping.md).

Three deterministic functions:

* map_detailed(name, primary, secondary, category): free-exercise-db's coarse muscle names
  plus name keywords -> the 54 taxonomy-v2 keys. Rules live in library_data/muscle_rules.json
  (research §5): per coarse muscle the FIRST matching rule wins, primary scaled 1.0 and
  secondary 0.5; add-ons (serratus on push-ups, grip on hangs...) apply unscaled; weights
  combine with max and anything under the 0.2 floor is dropped.
* translate_legacy(weights): v7 region weights -> v2 keys through the research §8 table
  (copy, not split: the main child keeps the region's full weight so readiness does not jump
  on migration day). Keys that are already v2 pass through.
* to_legacy(weights): v2 -> v7 regions (max per region), for the migration's downgrade.

Weights are estimates for a fatigue model, not measured muscle activation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.modules.progress.taxonomy import LEGACY_REGIONS, MUSCLE_BY_KEY

MAP_VERSION = "muscle-map-v1"
RULES_FILE = Path(__file__).resolve().parents[1] / "workouts" / "library_data" / "muscle_rules.json"

# research §8: each v7 region -> v2 keys and weights
LEGACY_TO_V2: dict[str, dict[str, float]] = {
    "upper_chest": {"pec_major_clavicular": 1.0, "pec_major_sternal": 0.5},
    "lower_chest": {"pec_major_sternal": 1.0, "pec_major_clavicular": 0.5, "pec_minor": 0.25},
    "front_delts": {"deltoid_anterior": 1.0},
    "side_delts": {"deltoid_lateral": 1.0, "supraspinatus": 0.25},
    "rear_delts": {"deltoid_posterior": 1.0, "infraspinatus": 0.5, "teres_minor": 0.5},
    "biceps": {"biceps_long": 1.0, "biceps_short": 1.0, "brachialis": 0.75, "brachioradialis": 0.5},
    "triceps": {"triceps_lateral": 1.0, "triceps_medial": 1.0, "triceps_long": 0.75},
    "forearms": {"wrist_flexors": 1.0, "wrist_extensors": 0.75, "brachioradialis": 0.5},
    "traps": {"trap_upper": 1.0, "trap_middle": 0.5, "trap_lower": 0.25},
    "lats": {"latissimus_dorsi": 1.0, "teres_major": 0.75, "trap_lower": 0.25},
    "rhomboids": {"rhomboids": 1.0, "trap_middle": 1.0, "deltoid_posterior": 0.25},
    "lower_back": {"erector_spinae": 1.0, "quadratus_lumborum": 0.5},
    "abs": {
        "rectus_abdominis": 1.0,
        "external_obliques": 0.5,
        "internal_obliques": 0.5,
        "transversus_abdominis": 0.25,
    },
    "obliques": {"external_obliques": 1.0, "internal_obliques": 1.0, "quadratus_lumborum": 0.25},
    "glutes": {
        "gluteus_maximus": 1.0,
        "gluteus_medius": 0.5,
        "gluteus_minimus": 0.25,
        "tensor_fasciae_latae": 0.25,
    },
    "quads": {
        "vastus_lateralis": 1.0,
        "vastus_medialis": 1.0,
        "vastus_intermedius": 1.0,
        "rectus_femoris": 0.75,
    },
    "hamstrings": {"biceps_femoris": 1.0, "semitendinosus": 1.0, "semimembranosus": 1.0},
    "adductors": {"adductor_longus": 1.0, "adductor_magnus": 1.0, "gracilis": 0.5},
    "calves": {"gastrocnemius": 1.0, "soleus": 1.0},
}

# A v7 region -> the free-exercise-db coarse name whose rules refine it by keyword
# (used for new custom exercises, whose first guess is still made per region).
LEGACY_TO_COARSE: dict[str, str] = {
    "upper_chest": "chest",
    "lower_chest": "chest",
    "front_delts": "shoulders",
    "side_delts": "shoulders",
    "rear_delts": "shoulders",
    "biceps": "biceps",
    "triceps": "triceps",
    "forearms": "forearms",
    "traps": "traps",
    "lats": "lats",
    "rhomboids": "middle back",
    "lower_back": "lower back",
    "abs": "abdominals",
    "obliques": "abdominals",
    "glutes": "glutes",
    "quads": "quadriceps",
    "hamstrings": "hamstrings",
    "adductors": "adductors",
    "calves": "calves",
}


@lru_cache(maxsize=1)
def rules() -> dict[str, Any]:
    with RULES_FILE.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


@lru_cache(maxsize=512)
def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def map_detailed(
    name: str,
    primary: Iterable[str],
    secondary: Iterable[str] = (),
    category: str | None = None,
) -> dict[str, float]:
    """free-exercise-db coarse muscles + the exercise name -> v2 key weights."""
    r = rules()
    low = name.lower()
    zero = r["zero_load"]
    if category in zero["categories"] or _rx(zero["name_regex"]).search(low):
        return {}
    out: dict[str, float] = {}

    def put(key: str, w: float) -> None:
        out[key] = max(out.get(key, 0.0), w)

    for muscles, scale in ((primary, r["scale"]["primary"]), (secondary, r["scale"]["secondary"])):
        for m in muscles:
            for rule in r["region_rules"].get(m, []):
                if rule["regex"] == "" or _rx(rule["regex"]).search(low):
                    for key, w in rule["weights"].items():
                        put(key, w * scale)
                    break
    for rule in r["addons"]:
        if _rx(rule["regex"]).search(low) and not (
            rule.get("exclude") and _rx(rule["exclude"]).search(low)
        ):
            for key, w in rule["weights"].items():
                put(key, w)
    return {k: round(w, 3) for k, w in sorted(out.items()) if w >= r["floor"]}


def translate_legacy(weights: Mapping[str, float]) -> dict[str, float]:
    """v7 region weights -> v2 keys (new weight = old x table weight, combined with max)."""
    out: dict[str, float] = {}
    for key, w in weights.items():
        targets = LEGACY_TO_V2.get(key)
        if targets is None:
            if key in MUSCLE_BY_KEY:
                out[key] = max(out.get(key, 0.0), w)
            continue
        for new, tw in targets.items():
            out[new] = max(out.get(new, 0.0), round(w * tw, 3))
    return {k: w for k, w in sorted(out.items()) if w >= rules()["floor"]}


def refine_legacy(weights: Mapping[str, float], name: str) -> dict[str, float]:
    """A first guess made per v7 region, sharpened by the name's keywords (incline, hammer,
    seated calf...). Regions with no coarse equivalent fall back to translate_legacy."""
    primary = sorted(
        {LEGACY_TO_COARSE[k] for k, w in weights.items() if k in LEGACY_TO_COARSE and w >= 1.0}
    )
    secondary = sorted(
        {LEGACY_TO_COARSE[k] for k, w in weights.items() if k in LEGACY_TO_COARSE and w < 1.0}
        - set(primary)
    )
    out = map_detailed(name, primary, secondary)
    passthrough = {k: w for k, w in weights.items() if k in MUSCLE_BY_KEY}
    for k, w in translate_legacy(passthrough).items():
        out[k] = max(out.get(k, 0.0), w)
    return out


def to_legacy(weights: Mapping[str, float]) -> dict[str, float]:
    """v2 keys -> v7 regions (max per region); keys with no v7 region are dropped."""
    out: dict[str, float] = {}
    for key, w in weights.items():
        if key in LEGACY_REGIONS:
            out[key] = max(out.get(key, 0.0), w)
            continue
        m = MUSCLE_BY_KEY.get(key)
        if m is None or not m.legacy:
            continue
        out[m.legacy] = max(out.get(m.legacy, 0.0), w)
    return out
