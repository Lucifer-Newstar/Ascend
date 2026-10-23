"""trainer-intents-v1: what a chat message is asking for, decided by rules before any AI.

The order matters: actions and app questions are recognised first, so a greeting, a "what
can you do" or a "start fresh" never reaches the local model and never gets an unrelated
training tip (the 1.0.0 coach answered every question with the day's muscle tip when the
model timed out). Only messages that match nothing here go to the AI, if it is on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.modules.trainer import kb

IntentKind = Literal[
    "greeting",
    "help",
    "thanks",
    "identity",
    "erase",
    "tour",
    "navigate",
    "plan_workout",
    "plan_diet",
    "goal_check",
    "change_trainer",
    "train_today",
    "missed_day",
    "feeling",
    "program_pick",
    "action",
    "faq",
    "why",
    "unknown",
]


@dataclass(frozen=True)
class Intent:
    kind: IntentKind
    section: str | None = None
    entry: kb.Entry | None = None
    numbers: dict[str, float] = field(default_factory=dict)


_GREETING = re.compile(
    r"^\s*(hi+|hello+|hey+|yo|hola|namaste|vanakkam|sup|good (morning|afternoon|evening))\b", re.I
)
_HELP = re.compile(
    r"\b(what can you do|what do you do|how can you help|help me|^help$|what are you for|"
    r"what can i (ask|do here)|commands)\b",
    re.I,
)
_THANKS = re.compile(r"\b(thanks|thank you|thx|ty|cheers|appreciate it)\b", re.I)
_IDENTITY = re.compile(
    r"\b(who are you|what('s| is) your name|are you (an? )?(ai|bot|human))\b", re.I
)
_ERASE = re.compile(
    r"\b((erase|delete|wipe|reset|clear|remove)\b.*\b(data|everything|all|history|logs?)|"
    r"start (fresh|over|from scratch)|fresh start|none of (this|the) (data )?is mine|"
    r"not my data)",
    re.I,
)
_TOUR = re.compile(
    r"\b(tour|show me around|walk me through|guide me|give me a walkthrough|how do i use)\b", re.I
)
_NAVIGATE = re.compile(r"^\s*(open|go to|take me to|show me|switch to)\b", re.I)
_PLAN = re.compile(r"\b(make|build|create|generate|design|give me|need|want|plan|suggest)\b", re.I)
_DIET_WORDS = re.compile(r"\b(diet|meal|meals|food|nutrition|eating)\b", re.I)
_WORKOUT_WORDS = re.compile(
    r"\b(workout|training|program|programme|routine|split|gym) ?(plan)?\b", re.I
)
_PLAN_WORD = re.compile(r"\b(plan|program|programme|routine|split|chart)\b", re.I)
_CHANGE_TRAINER = re.compile(
    r"\b(change|switch|swap|pick|choose|new|different)\b.*\btrainers?\b", re.I
)
_TRAIN_TODAY = re.compile(
    r"\b(what (should|do|can) i (train|do|work)|today'?s (workout|tip|plan)|tip for today|"
    r"what to train|which muscles?|train today)\b",
    re.I,
)
_GOAL = re.compile(
    r"\b(lose|drop|cut|shed|gain|put on|bulk|add)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|kilos?|lbs?|pounds?)"
    r"(?:\s+\w+){0,3}?\s+(?:in|within|by)\s+(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|eight|ten|twelve)\s*"
    r"(days?|weeks?|months?)",
    re.I,
)
_WHY = re.compile(
    r"^\s*(why\??|why (did|do) you (say|post|send|tell me) (that|this)\??|"
    r"why (that|this)( message| tip| boss)?\??|what was that about\??|explain that)\s*$",
    re.I,
)
_ACTION = re.compile(
    r"^\s*(log|add|record|track|switch me|follow|start|weigh(ed)?|i weigh|i ate|ate|had)\b", re.I
)


_COUNT_WORDS: dict[str, float] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "eight": 8,
    "ten": 10,
    "twelve": 12,
}


def goal_numbers(text: str) -> dict[str, float] | None:
    m = _GOAL.search(text)
    if not m:
        return None
    verb, amount, unit, n, period = m.groups()
    count = _COUNT_WORDS.get(n.lower()) if not n[0].isdigit() else float(n)
    assert count is not None
    kg = float(amount) * (0.4536 if unit.lower().startswith(("lb", "pound")) else 1.0)
    weeks = count * {"d": 1 / 7, "w": 1.0, "m": 4.345}[period.lower()[0]]
    sign = -1.0 if verb.lower() in ("lose", "drop", "cut", "shed") else 1.0
    return {"change_kg": round(sign * kg, 2), "weeks": round(weeks, 2)}


# v1.2 beginner intents (answered by rules, no model needed).
_MISSED = re.compile(
    r"\b(missed|skipped|skip(ped)?|couldn'?t (train|work ?out|go)"
    r"|did(n'?t| not) (train|work ?out|go)|no workout|bunked)\b"
    r".*\b(yesterday|today|day|session|workout|gym|training)\b"
    r"|\b(yesterday|today)\b.*\b(missed|skipped)\b",
    re.I,
)
_FEELING = re.compile(
    r"\b(overwhelm\w*|demotivat\w*|unmotivat\w*|no motivation|lazy|stressed|burn(ed|t)? out|"
    r"give up|giving up|can'?t do (this|it)|too hard|feel(ing)? (bad|low|down|sad|tired)|"
    r"exhausted|so tired)\b",
    re.I,
)
_PROGRAM_PICK = re.compile(
    r"\b(what|which|best|good|suggest|recommend)\b.*\b(program|programme|routine|plan)\b"
    r"|\bonly have (a |an )?(pull ?-?up bar|dumbbells?|rings|no equipment|nothing)\b",
    re.I,
)


def classify(text: str) -> Intent:
    t = text.strip()
    if not t:
        return Intent("help")
    if _WHY.search(t):
        return Intent("why")
    if _ERASE.search(t):
        return Intent("erase")
    if _MISSED.search(t):
        return Intent("missed_day")
    if _FEELING.search(t):
        return Intent("feeling")
    nums = goal_numbers(t)
    if nums:
        return Intent("goal_check", numbers=nums)
    if _ACTION.search(t):
        return Intent("action")
    if _CHANGE_TRAINER.search(t):
        return Intent("change_trainer")
    if _TOUR.search(t):
        return Intent("tour", section=kb.section_in(t))
    if _PROGRAM_PICK.search(t) and not _DIET_WORDS.search(t):
        return Intent("program_pick")
    if _PLAN.search(t) and _PLAN_WORD.search(t):
        if _DIET_WORDS.search(t):
            return Intent("plan_diet")
        if _WORKOUT_WORDS.search(t) or _PLAN_WORD.search(t):
            return Intent("plan_workout")
    if _NAVIGATE.search(t):
        section = kb.section_in(t)
        if section:
            return Intent("navigate", section=section)
    if _TRAIN_TODAY.search(t):
        return Intent("train_today")
    words = kb.words(t)
    if _GREETING.search(t) and len(words) <= 5:
        return Intent("greeting")
    if _HELP.search(t):
        return Intent("help")
    if _THANKS.search(t) and len(words) <= 6:
        return Intent("thanks")
    if _IDENTITY.search(t):
        return Intent("identity")
    entry = kb.match(t)
    if entry is not None:
        return Intent("faq", section=entry.section, entry=entry)
    return Intent("unknown")
