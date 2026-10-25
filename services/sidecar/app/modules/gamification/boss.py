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

ALGO_VERSION = "boss-v2"
BONUS_XP = 150  # a C-tier boss; see TIER_BONUS_XP
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

# boss-v2 (v1.2): every boss has a tier (E to S, the same letters as hunter ranks) and a
# display category (strength, calisthenics, cardio, martial arts). The tier scales the HP
# and the bonus, so the ladder climbs: an E boss is a lighter week than an S boss.
TIERS = ("E", "D", "C", "B", "A", "S")
BOSS_TIER: dict[str, str] = {
    "Iron Golem": "E",
    "Ash Wyvern": "E",
    "Frost Colossus": "D",
    "Stone Basilisk": "D",
    "Storm Chimera": "C",
    "Grave Warden": "C",
    "Crimson Ogre": "B",
    "Obsidian Hydra": "B",
    "Thunder Behemoth": "A",
    "Venom Manticore": "A",
    "Dusk Leviathan": "A",
    "Bone Titan": "S",
}
BOSS_CATEGORY: dict[str, str] = {
    "Iron Golem": "strength",
    "Frost Colossus": "strength",
    "Grave Warden": "strength",
    "Thunder Behemoth": "strength",
    "Bone Titan": "strength",
    "Stone Basilisk": "calisthenics",
    "Storm Chimera": "calisthenics",
    "Obsidian Hydra": "calisthenics",
    "Ash Wyvern": "cardio",
    "Dusk Leviathan": "cardio",
    "Crimson Ogre": "martial_arts",
    "Venom Manticore": "martial_arts",
}
TIER_HP_SCALE = {"E": 0.8, "D": 0.9, "C": 1.0, "B": 1.1, "A": 1.2, "S": 1.3}
TIER_BONUS_XP = {"E": 100, "D": 125, "C": 150, "B": 175, "A": 200, "S": 250}
LEVEL_TIER = {"beginner": "D", "intermediate": "B", "advanced": "A", "expert": "S"}


@dataclass(frozen=True)
class Season:
    """A limited-time boss: it shows up every other week while its season runs (the
    first week of the season included) and drops its own cosmetic when beaten. Its tier
    follows your level, so it is a fair fight at every rank."""

    boss: str
    title: str
    name: str  # the season's name, shown on the boss card
    months: tuple[int, ...]
    category: str
    drop: str  # the cosmetic it drops (frontend catalog id)


SEASONS: tuple[Season, ...] = (
    Season("Winter Wraith", "Wraithbane", "Winter", (12, 1, 2), "cardio", "pet_spirit_wolf"),
    Season(
        "Shadow Sovereign",
        "Sovereign's Bane",
        "Shadow Season",
        (3, 4, 5),
        "strength",
        "outfit_shadow_monarch",
    ),
    Season(
        "Monsoon Serpent",
        "Serpent Tamer",
        "Monsoon",
        (6, 7, 8, 9),
        "calisthenics",
        "weapon_energy_gauntlet",
    ),
    Season(
        "Harvest Colossus",
        "Harvest Breaker",
        "Harvest Festival",
        (10, 11),
        "martial_arts",
        "outfit_harvest_festival",
    ),
)
SEASON_BY_BOSS = {s.boss: s for s in SEASONS}


def season_for(d: date) -> Season:
    return next(s for s in SEASONS if d.month in s.months)


def season_start(week: date) -> date:
    """The first Monday of the season that `week` (a Monday) belongs to."""
    season = season_for(week)
    year = week.year if week.month >= season.months[0] else week.year - 1
    first_day = date(year, season.months[0], 1)
    return first_day + timedelta(days=(7 - first_day.weekday()) % 7)


def season_end(week: date) -> date:
    """The last day of the season that `week` belongs to."""
    season = season_for(week)
    d = week
    while season_for(d + timedelta(days=1)) is season:
        d += timedelta(days=1)
    return d


def seasonal_week(week: date) -> bool:
    """Is the seasonal boss out this week? The first week of a season, then every other
    week until the season ends."""
    return ((week - season_start(week)).days // 7) % 2 == 0


def tier_of(name: str, level: str | None = None) -> str:
    if name in SEASON_BY_BOSS:
        return LEVEL_TIER.get(level or "beginner", "D")
    return BOSS_TIER.get(name, "C")


def category_of(name: str) -> str:
    if name in SEASON_BY_BOSS:
        return SEASON_BY_BOSS[name].category
    return BOSS_CATEGORY.get(name, "strength")


def bonus_for(tier: str) -> int:
    return TIER_BONUS_XP.get(tier, BONUS_XP)


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
    seasonal: bool = False,
) -> tuple[str, str]:
    """The boss and title for the week that starts on `week` (a Monday). Without a level,
    the fixed rotation of all twelve; with one, a rotation over the bosses that level may
    face, preferring the one that guards `under` (the most under-trained category). With
    `seasonal`, a seasonal week brings the season's boss instead (never on a low-readiness
    day)."""
    if seasonal and not low_readiness and seasonal_week(week):
        s = season_for(week)
        return (s.boss, s.title)
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


def scaled(hp: Hp, tier: str) -> Hp:
    """The tier's share of a week's training (E 80% ... S 130%)."""
    k = TIER_HP_SCALE.get(tier, 1.0)
    if k == 1.0:
        return hp
    return Hp(clamp(hp.hp * k), hp.source, f"{hp.note}; tier {tier}: x{k:g}")


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
