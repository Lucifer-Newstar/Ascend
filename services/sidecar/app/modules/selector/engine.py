"""select-v1: pick what the trainer says today, and remember why.

1. Eligibility: every condition true, the level inside [min_level, max_level], readiness
   inside the item's range, and the safety gates (no `hard` item when readiness < 50, no
   `deficit` item when intake is already low or the user is under 18).
2. Cooldown: an item shown within its cooldown_days is skipped.
3. Rank: priority, then the item id (deterministic).
4. Caps: at most DAILY_CAP items a day across everything the trainer posts (watcher events
   included), at most KIND_CAP of each kind, and one item per training category.
Each pick keeps its "why": the sentences of the conditions that matched, with the numbers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.modules.selector.catalog import Item
from app.modules.selector.state import PlayerState, level_rank

ENGINE_VERSION = "select-v1"
DAILY_CAP = 3
KIND_CAP: dict[str, int] = {"alert": 2, "message": 2, "tip": 2, "quest": 1, "tour": 1}


@dataclass(frozen=True)
class Pick:
    item: Item
    text: str
    why: list[str]


@dataclass
class Verdict:
    eligible: bool
    why: list[str] = field(default_factory=list)
    blocked_by: str | None = None


class _Facts(dict[str, object]):
    def __missing__(self, key: str) -> str:
        return "?"


def fmt(template: str, facts: Mapping[str, object]) -> str:
    return template.format_map(_Facts(facts))


def check(item: Item, s: PlayerState) -> Verdict:
    facts = s.facts()
    rank = level_rank(s.level)
    if rank < level_rank(item.min_level) or rank > level_rank(item.max_level):
        return Verdict(False, blocked_by=f"level {s.level}")
    lo, hi = item.readiness
    if not lo <= s.readiness <= hi:
        return Verdict(False, blocked_by=f"readiness {s.readiness}")
    if item.hard and s.low_readiness:
        return Verdict(False, blocked_by="safety: low readiness")
    if item.deficit and (s.intake_low or s.under_18):
        return Verdict(False, blocked_by="safety: intake already low or under 18")
    why: list[str] = []
    for c in item.conds:
        if not c.test(s):
            return Verdict(False, blocked_by=f"condition {c.id}")
        why.append(fmt(c.why, facts))
    if item.min_level != "beginner" or item.max_level != "expert":
        why.append(f"it is meant for your level ({s.level})")
    return Verdict(True, why)


def select(
    s: PlayerState,
    items: Iterable[Item],
    last_shown: Mapping[str, date],
    today: date,
    shown_today: Mapping[str, int] | None = None,
    cap: int = DAILY_CAP,
) -> list[Pick]:
    """The items to post today. `last_shown` is item id -> the last day it was posted;
    `shown_today` is kind -> how many posts of that kind (watcher events included) today."""
    counts: dict[str, int] = dict(shown_today or {})
    left = cap - sum(counts.values())
    picks: list[Pick] = []
    used_categories: set[str] = set()
    ranked = sorted(items, key=lambda i: (-i.priority, i.id))
    for item in ranked:
        if left <= 0:
            break
        last = last_shown.get(item.id)
        if last is not None and (today - last).days < item.cooldown_days:
            continue
        if counts.get(item.kind, 0) >= KIND_CAP.get(item.kind, 1):
            continue
        if item.category and item.category in used_categories:
            continue
        v = check(item, s)
        if not v.eligible:
            continue
        picks.append(Pick(item, fmt(item.text, s.facts()), v.why))
        counts[item.kind] = counts.get(item.kind, 0) + 1
        if item.category:
            used_categories.add(item.category)
        left -= 1
    return picks
