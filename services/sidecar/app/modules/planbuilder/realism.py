"""How realistic a weight goal is (planbuilder-v1).

Healthy gain is about 0.25-0.5 kg a week and healthy loss about 0.25-0.75 kg a week. More
than 1 kg a week either way is flagged as not something the trainer will plan, with a
realistic and a stretch target instead. No body or body-fat comments, no medical claims:
only the pace.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

GAIN = (0.25, 0.5)
LOSS = (0.25, 0.75)
LIMIT = 1.0  # kg a week, either way


@dataclass(frozen=True)
class WeightCheck:
    ok: bool
    message: str
    realistic_kg: float | None = None
    stretch_kg: float | None = None


def _kg(x: float) -> str:
    return f"{round(x, 1):g} kg"


def check(current: float, target: float, weeks: int | None) -> WeightCheck:
    diff = round(target - current, 1)
    if abs(diff) < 0.5:
        return WeightCheck(True, f"You're already about there: {_kg(current)} now.")
    gain = diff > 0
    lo, hi = GAIN if gain else LOSS
    word = "gain" if gain else "lose"
    sign = 1 if gain else -1
    if weeks:
        rate = abs(diff) / weeks
        realistic = round(current + sign * lo * weeks, 1)
        stretch = round(current + sign * hi * weeks, 1)
        if rate > LIMIT:
            return WeightCheck(
                False,
                f"{_kg(abs(diff))} in {weeks} weeks is {rate:.1f} kg a week. That's faster than "
                f"is healthy, so I won't plan it: most of it would be water and fat, not "
                f"muscle. At {lo:g}-{hi:g} kg a week, {weeks} weeks gets you to about "
                f"{_kg(realistic)} (realistic) or {_kg(stretch)} (stretch).",
                realistic,
                stretch,
            )
        if rate > hi:
            return WeightCheck(
                True,
                f"{rate:.2f} kg a week is on the fast side; {lo:g}-{hi:g} kg a week is the steady "
                f"pace. I'll plan for {_kg(stretch)} in {weeks} weeks and we'll see.",
                realistic,
                stretch,
            )
        return WeightCheck(True, f"{rate:.2f} kg a week is a pace you can hold. Good target.")
    slow = math.ceil(abs(diff) / lo)
    fast = math.ceil(abs(diff) / hi)
    first = min(abs(diff), round(hi * 6, 1))
    return WeightCheck(
        True,
        f"To {word} {_kg(abs(diff))} at a healthy {lo:g}-{hi:g} kg a week takes about "
        f"{fast}-{slow} weeks. A good first stop: {_kg(current + sign * first)} in 6 weeks.",
        round(current + sign * lo * 6, 1),
        round(current + sign * first, 1),
    )
