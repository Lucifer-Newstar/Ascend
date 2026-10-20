"""Morning check-in -> readiness score (deterministic, versioned).

  readiness = 100 x (0.35 sleep + 0.30 energy + 0.20 (1 - soreness) + 0.15 mood)

Each input is scaled to 0-1 first: the 1-5 scales map to (x - 1) / 4 and
soreness maps none / some / a lot to 0 / 0.5 / 1. The weights are estimates
(docs/ai/adaptive-planning-ai.md section 7), not a validated instrument.

Bands: green >= 70, amber 50-69, red < 50.
  green -> today's plan unchanged
  amber -> the training quest is cut by one set
  red   -> the training quest is swapped for mobility
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FORMULA_VERSION = "readiness-v1"
W_SLEEP, W_ENERGY, W_SORENESS, W_MOOD = 0.35, 0.30, 0.20, 0.15
GREEN_AT, AMBER_AT = 70, 50
SORENESS_SCALE = {"none": 0.0, "some": 0.5, "a_lot": 1.0}

Band = Literal["green", "amber", "red"]
Soreness = Literal["none", "some", "a_lot"]

ADJUSTMENT: dict[str, str] = {
    "green": "Today's plan is unchanged.",
    "amber": "Today's training quest is one set shorter.",
    "red": "Today's training quest is swapped for 15 minutes of mobility.",
}


def _unit(score: int) -> float:
    if not 1 <= score <= 5:
        raise ValueError("scores are 1-5")
    return (score - 1) / 4


@dataclass(frozen=True)
class Readiness:
    score: int
    band: Band
    adjustment: str


def band_for(score: int) -> Band:
    if score >= GREEN_AT:
        return "green"
    if score >= AMBER_AT:
        return "amber"
    return "red"


def readiness(sleep: int, energy: int, soreness: Soreness, mood: int) -> Readiness:
    raw = (
        W_SLEEP * _unit(sleep)
        + W_ENERGY * _unit(energy)
        + W_SORENESS * (1 - SORENESS_SCALE[soreness])
        + W_MOOD * _unit(mood)
    )
    score = round(100 * raw)
    band = band_for(score)
    return Readiness(score=score, band=band, adjustment=ADJUSTMENT[band])
