"""Captions for share cards (share-v1). Pure functions of the achievement, no AI.

A caption only carries what the card shows: the achievement itself. Never body weight,
body measurements, photos, age or anything from the profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

SHARE_VERSION = "share-v1"
HASHTAGS = ("#ASCEND", "#calisthenics")
X_INTENT = "https://x.com/intent/tweet?text="
X_LIMIT = 280
KINDS = ("pr", "skill", "streak", "boss", "program", "rank")


class ShareError(ValueError):
    pass


@dataclass(frozen=True)
class Card:
    kind: str
    title: str
    headline: str
    detail: str
    caption: str
    x_url: str


def _s(payload: dict[str, object], key: str, limit: int = 60) -> str:
    v = payload.get(key)
    if v is None or str(v).strip() == "":
        raise ShareError(f"missing '{key}' for this card")
    return str(v).strip()[:limit]


def _n(payload: dict[str, object], key: str) -> float:
    v = payload.get(key)
    if not isinstance(v, int | float) or isinstance(v, bool) or v <= 0 or v > 100000:
        raise ShareError(f"'{key}' must be a positive number")
    return float(v)


def build(payload: dict[str, object]) -> Card:
    kind = str(payload.get("kind", ""))
    if kind == "pr":
        ex, kg = _s(payload, "exercise"), _n(payload, "e1rm_kg")
        title, headline = "New personal record", f"{ex}: {kg:g} kg"
        detail = "Estimated one-rep max"
        text = f"New PR on {ex}: an estimated {kg:g} kg one-rep max."
    elif kind == "skill":
        skill, step = _s(payload, "skill"), _s(payload, "step")
        title, headline, detail = "Skill unlocked", step, skill
        text = f"Unlocked {step} on the way to the {skill}."
    elif kind == "streak":
        days = int(_n(payload, "days"))
        title, headline, detail = "Streak", f"{days} days", "Showed up every day"
        text = f"{days}-day training streak."
    elif kind == "boss":
        boss, earned = _s(payload, "boss"), _s(payload, "title")
        title, headline, detail = "Boss defeated", boss, f"Title earned: {earned}"
        text = f"Beat this week's boss, {boss}, and earned the title {earned}."
    elif kind == "program":
        program, sessions = _s(payload, "program"), int(_n(payload, "sessions"))
        title, headline, detail = "Block complete", program, f"{sessions} sessions"
        text = f"Finished a block of {program}: {sessions} sessions."
    elif kind == "rank":
        rank = _s(payload, "rank", 24)
        title, headline, detail = "Rank up", f"Rank {rank}", "Hunter rank"
        text = f"Reached rank {rank}."
    else:
        raise ShareError(f"kind must be one of {', '.join(KINDS)}")
    caption = f"{text} Tracked with ASCEND. {' '.join(HASHTAGS)}"
    if len(caption) > X_LIMIT:
        caption = caption[: X_LIMIT - 1] + "\u2026"
    return Card(kind, title, headline, detail, caption, X_INTENT + quote(caption, safe=""))
