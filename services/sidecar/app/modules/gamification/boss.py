"""Weekly boss raid (boss-v1, ADR-0022): one boss a week, beaten by training.

A boss appears each Monday. Its HP is a week of your training: the working sets of the
program you follow (halved in a deload week), else the median number of sets you logged
per week over the 4 weeks before, else a starter value. Every set you log that week deals
1 damage (mobility and meditation sets do not). Beat it by Sunday for a one-off XP bonus
and the boss's title on your Hunter profile. Missing it costs nothing.

Pure and deterministic: the same logs give the same boss, HP and outcome.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

ALGO_VERSION = "boss-v1"
BONUS_XP = 150
HP_MIN = 12
HP_MAX = 150
HP_STARTER = 20
HISTORY_WEEKS = 4
# Sets in these sections are training volume; mobility and meditation are not.
DAMAGE_SECTIONS = frozenset({"gym", "calisthenics", "martial_arts", "cardio"})

# (boss, title earned by beating it). Original names, one a week in a fixed rotation.
BOSSES: tuple[tuple[str, str], ...] = (
    ("Iron Golem", "Golem Breaker"),
    ("Ash Wyvern", "Wyvern Slayer"),
    ("Frost Colossus", "Frostbreaker"),
    ("Stone Basilisk", "Basilisk Bane"),
    ("Storm Chimera", "Storm Tamer"),
    ("Grave Warden", "Wardenfall"),
    ("Crimson Ogre", "Ogre Crusher"),
    ("Obsidian Hydra", "Hydra Hunter"),
    ("Thunder Behemoth", "Behemoth Feller"),
    ("Venom Manticore", "Manticore Bane"),
    ("Dusk Leviathan", "Tidebreaker"),
    ("Bone Titan", "Titan Toppler"),
)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


# select-v1: each boss is a catalog item gated by experience level, tagged with the training
# category it "guards" (the selector prefers the boss of your most under-trained category,
# so the raid nudges balance). Advanced and expert bosses count as hard: never picked on a
# low-readiness day. (name -> minimum level, category)
BOSS_GATES: dict[str, tuple[str, str]] = {
    "Iron Golem": ("beginner", "push"),
    "Ash Wyvern": ("beginner", "cardio"),
    "Frost Colossus": ("beginner", "legs"),
    "Stone Basilisk": ("beginner", "core"),
    "Storm Chimera": ("intermediate", "pull"),
    "Grave Warden": ("intermediate", "legs"),
    "Crimson Ogre": ("intermediate", "push"),
    "Obsidian Hydra": ("intermediate", "calisthenics"),
    "Thunder Behemoth": ("advanced", "legs"),
    "Venom Manticore": ("advanced", "pull"),
    "Dusk Leviathan": ("advanced", "cardio"),
    "Bone Titan": ("expert", "push"),
}
LEVEL_ORDER = ("beginner", "intermediate", "advanced", "expert")


def eligible_bosses(level: str, low_readiness: bool = False) -> list[tuple[str, str]]:
    rank = LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 0
    out = []
    for name, title in BOSSES:
        need, _ = BOSS_GATES[name]
        need_rank = LEVEL_ORDER.index(need)
        if need_rank > rank or (low_readiness and need_rank >= 2):
            continue
        out.append((name, title))
    return out


def boss_for(
    week: date,
    level: str | None = None,
    under: str | None = None,
    low_readiness: bool = False,
) -> tuple[str, str]:
    """The boss and title for the week that starts on `week` (a Monday). Without a level,
    the fixed rotation of all twelve; with one, a rotation over the bosses that level may
    face, preferring the one that guards `under` (the most under-trained category)."""
    if level is None:
        return BOSSES[(week.toordinal() // 7) % len(BOSSES)]
    pool = eligible_bosses(level, low_readiness) or list(BOSSES[:1])
    preferred = [b for b in pool if under and BOSS_GATES[b[0]][1] == under]
    pool = preferred or pool
    return pool[(week.toordinal() // 7) % len(pool)]


@dataclass(frozen=True)
class Hp:
    hp: int
    source: str  # "program" | "history" | "starter"
    note: str


def clamp(n: float) -> int:
    return int(max(HP_MIN, min(HP_MAX, round(n))))


def hp_for(
    program_sets: int | None,
    program_name: str | None,
    deload_week: bool,
    weekly_sets: Sequence[int],
) -> Hp:
    """HP for a new week. `weekly_sets` are the set counts of the weeks before, oldest first."""
    if program_sets:
        raw = program_sets / 2 if deload_week else program_sets
        half = " (halved: deload week)" if deload_week else ""
        return Hp(
            clamp(raw), "program", f"{program_name}: {program_sets} working sets a week{half}"
        )
    recent = list(weekly_sets)[-HISTORY_WEEKS:]
    if any(recent):
        med = statistics.median(recent)
        weeks = ", ".join(str(n) for n in recent)
        return Hp(clamp(med), "history", f"median of your last {len(recent)} weeks ({weeks} sets)")
    return Hp(HP_STARTER, "starter", "no training logged in the last 4 weeks: a starter boss")


@dataclass(frozen=True)
class Outcome:
    damage: int
    defeated_on: date | None  # the day of the set that brought HP to 0


def outcome(hp: int, set_days: Sequence[date]) -> Outcome:
    """Damage from this week's sets (one per set) and the day the boss fell, if it did."""
    days = sorted(set_days)
    return Outcome(len(days), days[hp - 1] if len(days) >= hp else None)
