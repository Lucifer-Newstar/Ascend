"""App themes (v1.2): which looks exist and which the player has unlocked.

Light and Dark are the v1.1 looks and stay free; Shadow is the free default for new
players; the other four are earned. Rules are data (THEMES), checked against the player's
own record (best streak, rank, bosses beaten). An unlock is kept for good: a broken streak
never takes a theme away (stored in settings as "themes_unlocked").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

RANK_ORDER = "EDCBAS"
UNLOCKED_KEY = "themes_unlocked"


@dataclass(frozen=True)
class Theme:
    key: str
    name: str
    tagline: str
    # None = free. Otherwise (kind, amount): ("streak", 7) best streak in days,
    # ("rank", "D") reach that rank, ("bosses", 1) weekly bosses beaten.
    rule: tuple[str, int | str] | None = None


THEMES: tuple[Theme, ...] = (
    Theme("shadow", "Shadow", "Night dungeon, chains and violet light"),
    Theme("dark", "Dark", "The original ASCEND look, dark"),
    Theme("light", "Light", "The original ASCEND look, light"),
    Theme("crimson", "Crimson Gate", "A red battlefield before a cracking gate", ("streak", 7)),
    Theme("frost", "Frost", "A frozen mountain fortress under the aurora", ("rank", "D")),
    Theme("emerald", "Emerald", "Jungle ruins wrapped in glowing vines", ("bosses", 1)),
    Theme("solar", "Solar Gold", "A sky-island arena at sunrise", ("rank", "C")),
)
THEME_BY_KEY = {t.key: t for t in THEMES}
DEFAULT_THEME = "shadow"


@dataclass(frozen=True)
class Record:
    best_streak: int
    rank: str
    bosses_beaten: int


def requirement(t: Theme) -> str:
    if t.rule is None:
        return "Free"
    kind, amount = t.rule
    if kind == "streak":
        return f"Reach a {amount}-day streak"
    if kind == "rank":
        return f"Reach rank {amount}"
    return "Beat your first weekly boss" if amount == 1 else f"Beat {amount} weekly bosses"


def earned(t: Theme, r: Record) -> bool:
    if t.rule is None:
        return True
    kind, amount = t.rule
    if kind == "streak":
        return r.best_streak >= int(amount)
    if kind == "rank":
        return RANK_ORDER.index(r.rank) >= RANK_ORDER.index(str(amount))
    return r.bosses_beaten >= int(amount)


def progress_text(t: Theme, r: Record) -> str:
    if t.rule is None:
        return ""
    kind, amount = t.rule
    if kind == "streak":
        return f"Best streak {r.best_streak} of {amount} days"
    if kind == "rank":
        return f"Rank {r.rank} now"
    return f"{r.bosses_beaten} of {amount} beaten"


def record(db: Session, now: datetime) -> Record:
    from app.modules.gamification import formulas as f
    from app.modules.gamification import service as game
    from app.modules.gamification.models import BossRaid

    letter, _ = f.rank_for_level(f.level_from_total(game.total_xp(db)).level)
    beaten = db.scalar(select(func.count(BossRaid.id)).where(BossRaid.defeated_at.is_not(None)))
    return Record(game.streak(db, now.date()).best, letter, int(beaten or 0))


def stored(db: Session) -> set[str]:
    from app.modules.progress.service import get_setting

    try:
        return set(json.loads(get_setting(db, UNLOCKED_KEY, "[]")))
    except ValueError:
        return set()


def unlocked(db: Session, now: datetime) -> set[str]:
    """Every theme the player may use now; new unlocks are saved so they stay."""
    from app.modules.progress.service import set_setting

    have = stored(db)
    r = record(db, now)
    now_open = {t.key for t in THEMES if t.key in have or earned(t, r)}
    newly = {k for k in now_open if THEME_BY_KEY[k].rule is not None} - have
    if newly:
        set_setting(db, UNLOCKED_KEY, json.dumps(sorted(have | newly)))
        db.flush()
    return now_open
