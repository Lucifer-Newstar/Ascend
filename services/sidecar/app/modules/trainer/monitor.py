"""watch-v1: the trainer as a watcher. Pure rules over facts the service reads.

The trainer does not plan; it notices. Each rule turns a fact about the user's log into a
short message with a stable key, so the same event is posted once (the service stores
keys). Numbers in a message are the engines' own numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

WATCH_VERSION = "watch-v1"

Mood = Literal["neutral", "proud", "warning", "hyped"]
STREAK_MILESTONES = (3, 7, 14, 30, 50, 100, 200, 365)
PHOTO_EVERY_DAYS = 30
FAST_LOSS_PCT = 1.0  # % body weight per week (goalcheck-v1)


@dataclass(frozen=True)
class Notice:
    key: str
    kind: str
    mood: Mood
    text: str
    action_kind: str | None = None  # "navigate" | "share" | "tour"
    action_target: str | None = None
    share: dict[str, object] | None = None


@dataclass(frozen=True)
class Facts:
    today: date
    has_profile: bool
    profile_since: date | None = None
    sessions_per_week: int = 3
    last_workout: date | None = None
    workouts_total: int = 0
    streak: int = 0
    prs: list[tuple[int, str, float, date]] = field(default_factory=list)  # set id, ex, e1rm, day
    over_muscles: list[str] = field(default_factory=list)
    stalled: list[str] = field(default_factory=list)
    weights: list[tuple[date, float]] = field(default_factory=list)  # oldest first
    goal: str | None = None
    unlocks: list[tuple[int, str, str, date]] = field(default_factory=list)  # id, skill, step, day
    boss: tuple[date, str, str] | None = None  # week, boss, title (defeated this week)
    photos_supported: bool = False
    last_photo: date | None = None
    program_done: tuple[str, int] | None = None  # program name, sessions done
    # v1.3: opt-in nudges (Settings), off by default (review 1.9).
    photo_reminder: bool = False
    weigh_in_reminder: bool = False
    # v1.3 (review M8): today's welcome-back bonus, with the reason given for the miss.
    welcome_back: tuple[date, int, str | None] | None = None  # day, xp, reason


def _missed(f: Facts) -> list[Notice]:
    gap = math.ceil(7 / max(1, f.sessions_per_week)) + 2
    if f.last_workout is None:
        if f.has_profile and f.profile_since and (f.today - f.profile_since).days >= 2:
            return [
                Notice(
                    "first_session",
                    "missed",
                    "neutral",
                    "No session logged yet. The first one is the hardest; open Train and log "
                    "anything, even ten minutes.",
                    "navigate",
                    "workout",
                )
            ]
        return []
    days = (f.today - f.last_workout).days
    if days < gap:
        return []
    return [
        Notice(
            f"missed:{f.last_workout.isoformat()}",
            "missed",
            "warning",
            f"It has been {days} days since your last session. A short one today keeps the habit "
            f"alive; I'll have the plan ready.",
            "navigate",
            "workout",
        )
    ]


def _streak(f: Facts) -> list[Notice]:
    if f.streak not in STREAK_MILESTONES:
        return []
    start = f.today - timedelta(days=f.streak - 1)
    return [
        Notice(
            f"streak:{f.streak}:{start.isoformat()}",
            "streak",
            "proud",
            f"{f.streak}-day streak. That is discipline, not luck.",
            "share",
            "streak",
            {"kind": "streak", "days": f.streak},
        )
    ]


def _prs(f: Facts) -> list[Notice]:
    return [
        Notice(
            f"pr:{set_id}",
            "pr",
            "proud",
            f"New record on {ex}: an estimated {e1rm:g} kg one-rep max.",
            "share",
            "pr",
            {"kind": "pr", "exercise": ex, "e1rm_kg": e1rm},
        )
        for set_id, ex, e1rm, day in f.prs
        if (f.today - day).days <= 3
    ]


def _overload(f: Facts) -> list[Notice]:
    if not f.over_muscles:
        return []
    names = ", ".join(f.over_muscles[:3])
    return [
        Notice(
            f"over:{f.today.isoformat()}",
            "overtraining",
            "warning",
            f"Over their weekly range: {names}. Give them a rest day and train something else "
            f"today.",
            "navigate",
            "progress",
        )
    ]


def _stalled(f: Facts) -> list[Notice]:
    week = f.today.isocalendar()
    return [
        Notice(
            f"stall:{ex}:{week.year}-{week.week}",
            "plateau",
            "warning",
            f"{ex} has stalled for two weeks. The engine will suggest a lighter reset; take it, "
            f"then build back.",
            "navigate",
            "workout",
        )
        for ex in f.stalled[:2]
    ]


def _weight(f: Facts) -> list[Notice]:
    out: list[Notice] = []
    if f.weights:
        last_day = f.weights[-1][0]
        if f.weigh_in_reminder and (f.today - last_day).days >= 10:
            out.append(
                Notice(
                    f"weighin:{last_day.isoformat()}",
                    "weigh_in",
                    "neutral",
                    "No weigh-in for over a week. One morning reading keeps your calorie target "
                    "honest.",
                    "navigate",
                    "progress",
                )
            )
        recent = [(d, w) for d, w in f.weights if (f.today - d).days <= 14]
        if len(recent) >= 4 and f.goal == "cut":
            span = (recent[-1][0] - recent[0][0]).days / 7
            if span >= 1:
                rate = (recent[0][1] - recent[-1][1]) / span
                pct = rate / recent[0][1] * 100
                if pct > FAST_LOSS_PCT:
                    week = f.today.isocalendar()
                    out.append(
                        Notice(
                            f"fastloss:{week.year}-{week.week}",
                            "weight_trend",
                            "warning",
                            f"You are losing about {rate:.1f} kg a week ({pct:.1f}% of body "
                            f"weight). Faster than 1% costs muscle; eat a little more.",
                            "navigate",
                            "diet",
                        )
                    )
    return out


def _photo(f: Facts) -> list[Notice]:
    if not f.photo_reminder or not f.photos_supported or not f.has_profile:
        return []
    month = f.today.strftime("%Y-%m")
    if f.last_photo is None:
        if f.profile_since and (f.today - f.profile_since).days >= 7:
            text = "Take a first progress photo. Same spot, same light; you'll thank yourself."
        else:
            return []
    elif (f.today - f.last_photo).days >= PHOTO_EVERY_DAYS:
        text = "A month since your last progress photo. Time for this month's."
    else:
        return []
    return [Notice(f"photo:{month}", "photo_reminder", "neutral", text, "navigate", "profile")]


def _unlocks(f: Facts) -> list[Notice]:
    return [
        Notice(
            f"skill:{uid}",
            "skill",
            "hyped",
            f"Skill step unlocked: {step} ({skill}).",
            "share",
            "skill",
            {"kind": "skill", "skill": skill, "step": step},
        )
        for uid, skill, step, day in f.unlocks
        if (f.today - day).days <= 3
    ]


def _boss(f: Facts) -> list[Notice]:
    if f.boss is None:
        return []
    week, name, title = f.boss
    return [
        Notice(
            f"boss:{week.isoformat()}",
            "boss",
            "hyped",
            f"{name} is down. You earned the title {title}.",
            "share",
            "boss",
            {"kind": "boss", "boss": name, "title": title},
        )
    ]


def _program(f: Facts) -> list[Notice]:
    if f.program_done is None:
        return []
    name, sessions = f.program_done
    return [
        Notice(
            f"program:{name}:{sessions}",
            "program",
            "proud",
            f"{sessions} sessions of {name} done. That is a full block; ask me for the next plan.",
            "share",
            "program",
            {"kind": "program", "program": name, "sessions": sessions},
        )
    ]


def _welcome_back(f: Facts) -> list[Notice]:
    if f.welcome_back is None:
        return []
    day, xp, reason = f.welcome_back
    said = f" You told me \u201c{reason}\u201d; that happens." if reason else ""
    return [
        Notice(
            f"welcome:{day.isoformat()}",
            "welcome_back",
            "proud",
            f"Welcome back.{said} Coming back is the part that counts: +{xp} XP.",
        )
    ]


RULES = (
    _welcome_back, _prs, _unlocks, _boss, _streak, _program, _overload, _stalled, _weight,
    _missed, _photo,
)  # fmt: skip


def watch(f: Facts) -> list[Notice]:
    """Every notice the facts call for, most important first."""
    return [n for rule in RULES for n in rule(f)]
