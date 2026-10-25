"""The plan builder in the trainer chat (planbuilder-v1).

Main path: facts mentioned in normal chat become one "update your plan with this?" card.
Optional path: "Build my plan" starts a short interview with tap-to-answer chips, one
question at a time, and ends with the same card. Both work with the AI off; nothing is
saved before the card is confirmed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.planbuilder import realism
from app.modules.planbuilder.extract import Picked, extract
from app.modules.planbuilder.facts import PlanFacts, merge
from app.modules.trainer import chat
from app.modules.trainer.schemas import ChatAction, ChatOut

INTERVIEW_KEY = "planbuilder.interview"
_START = re.compile(
    r"^(build|make|create|plan)\s+(me\s+)?(my|a|me a)\s+(new\s+)?"
    r"(plan|week|weekly plan|training plan)( from scratch| for me| with me)?[.!]*$|"
    r"^plan builder$|^start the plan builder$"
)
_STOP = re.compile(r"^(stop|cancel|quit|never ?mind|forget it|exit|stop the plan builder)[.!]*$")
_SKIP = re.compile(r"^(skip|next|pass|not sure|idk|don'?t know)[.!]*$")

# (key, question, chips)
STEPS: list[tuple[str, str, list[str]]] = [
    ("goal", "Let's build your week. What's the main goal?",
     ["Gain weight", "Build muscle", "Lose fat", "Get stronger"]),
    ("weight", "Your weight now and where you'd like to be, if you have a number (\"42 kg to "
     "50 kg\")?", ["Skip"]),
    ("kit", "What do you have to train with? Dumbbells with their weights, a bar, rings, a bag, "
     "wraps, a gripper...", ["Nothing yet", "Skip"]),
    ("sports", "Any sport to mix in? Say when you last trained it, too (\"muay thai, 3 years "
     "ago\").", ["Muay Thai", "Kickboxing", "Boxing", "None"]),
    ("days", "How many days a week can you train, and about how long each time?",
     ["3 days", "4 days", "5 days", "45 minutes"]),
    ("appetite", "Last one: how's your appetite? Big meals easy, or easier to drink?",
     ["I eat fine", "I can't eat much but I can drink"]),
]  # fmt: skip
_GOAL_CHIP = {
    "gain weight": "gain_weight", "build muscle": "gain_muscle", "lose fat": "lose_fat",
    "get stronger": "strength",
}  # fmt: skip
_RANGE = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:kg)?\s*(?:to|->|→|-)\s*(\d{2,3}(?:\.\d)?)\s*(?:kg)?")
_DAYS_ONLY = re.compile(r"\b([2-6])\s*(?:days?|x)\b")
_MIN_ONLY = re.compile(r"\b(\d{2,3})\s*(?:min|mins|minutes)\b")
_SPORT_ONLY = {
    "muay thai": "muay_thai", "kickboxing": "kickboxing", "boxing": "boxing",
    "taekwondo": "taekwondo", "karate": "karate", "mma": "mma",
}  # fmt: skip


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").split()).strip(" .!")


# --- interview state (conversation state only; facts are saved on confirm) ---------------


def _state(db: Session) -> dict[str, Any] | None:
    from app.modules.progress import service as progress

    raw = progress.get_setting(db, INTERVIEW_KEY, "")
    try:
        return dict(json.loads(raw)) if raw else None
    except ValueError:
        return None


def _set_state(db: Session, state: dict[str, Any] | None) -> None:
    from app.modules.progress import service as progress

    progress.set_setting(db, INTERVIEW_KEY, json.dumps(state) if state else "")
    db.commit()


def _ask(step: int, lead: str = "") -> ChatOut:
    _, question, chips = STEPS[step]
    return ChatOut(
        reply=(lead + " " + question).strip(),
        mood="hyped" if step == 0 else "neutral",
        intent="plan_builder",
        source="rules",
        suggestions=chips + ["Stop"],
    )


def _answer(step_key: str, text: str) -> tuple[PlanFacts, list[str]]:
    """What one interview answer says, loosely (chips and short answers count)."""
    t = _norm(text)
    data: dict[str, Any] = {}
    kit: list[str] = []
    picked = extract(text) or extract(f"I have {text}" if step_key == "kit" else text)
    if picked is not None:
        data.update(picked.facts.model_dump(exclude_defaults=True))
        kit = list(picked.equipment_add)
    if step_key == "goal" and t in _GOAL_CHIP:
        data["goal"] = _GOAL_CHIP[t]
    if step_key == "weight":
        m = _RANGE.search(t)
        if m:
            data["weight_kg"], data["target_weight_kg"] = float(m.group(1)), float(m.group(2))
    if step_key == "sports":
        sports = [
            v
            for k, v in _SPORT_ONLY.items()
            if k in t and not (k == "boxing" and "kickboxing" in t)
        ]
        if sports:
            data["sports"] = list(dict.fromkeys([*data.get("sports", []), *sports]))
    if step_key == "days":
        m = _DAYS_ONLY.search(t)
        if m:
            data["days_per_week"] = int(m.group(1))
        m = _MIN_ONLY.search(t)
        if m and 10 <= int(m.group(1)) <= 120:
            data["session_minutes"] = int(m.group(1))
    if step_key == "appetite" and re.search(r"\b(fine|ok|okay|easy|good|normal)\b", t):
        data.setdefault("liquid_calories", False)
    return PlanFacts.model_validate(data), kit


def _weight_note(db: Session, f: PlanFacts) -> realism.WeightCheck | None:
    if f.target_weight_kg is None:
        return None
    from app.modules.progress import service as progress

    prof = progress.get_profile(db)
    current = f.weight_kg or (prof.weight_kg if prof is not None else None)
    if current is None:
        return None
    return realism.check(current, f.target_weight_kg, f.weeks)


def _card(
    db: Session, now: datetime, text: str, f: PlanFacts, kit: list[str], lead: str
) -> ChatOut:
    from app.modules.actions import service
    from app.modules.actions.chat_hook import _card as card_out
    from app.modules.actions.registry import ActionError

    try:
        row = service.propose(
            db, "build_plan", {"facts": f.model_dump(), "equipment_add": kit, "rebuild": True},
            "chat", text, now,
        )  # fmt: skip
    except ActionError as e:
        return ChatOut(reply=f"{lead} {e}".strip(), mood="neutral", intent="plan_builder",
                       source="rules")  # fmt: skip
    return ChatOut(
        reply=(lead + " Want me to update your plan with this? Check the card: confirm and it's "
               "done, and you can undo it after.").strip(),
        mood="hyped",
        intent="plan_builder",
        source="rules",
        proposal=card_out(db, row.id),
        actions=[ChatAction(kind="proposal", target=str(row.id), label="Review")],
    )  # fmt: skip


def _interview(db: Session, now: datetime, text: str, state: dict[str, Any]) -> ChatOut:
    t = _norm(text)
    if _STOP.match(t):
        _set_state(db, None)
        return ChatOut(
            reply="Stopped. Your plan is as it was; tell me things any time and I'll offer "
            "an update.",
            mood="neutral",
            intent="plan_builder",
            source="rules",
        )
    step = int(state.get("step", 0))
    got = PlanFacts.model_validate(state.get("facts") or {})
    kit = list(state.get("kit") or [])
    lead = ""
    if not _SKIP.match(t):
        new, new_kit = _answer(STEPS[step][0], text)
        if new.is_empty() and not new_kit and t not in ("nothing yet", "none", "no", "nothing"):
            return _ask(step, "I didn't catch that one; tap a chip or say Skip.")
        got = merge(got, new)
        kit += [k for k in new_kit if k not in kit]
        if STEPS[step][0] == "weight":
            check = _weight_note(db, got)
            if check is not None:
                lead = check.message
                if not check.ok and check.stretch_kg is not None:
                    got = got.model_copy(update={"target_weight_kg": check.stretch_kg})
                    lead += f" I'll plan for {check.stretch_kg:g} kg."
    step += 1
    if step < len(STEPS):
        _set_state(db, {"step": step, "facts": got.model_dump(exclude_defaults=True), "kit": kit})
        return _ask(step, lead)
    _set_state(db, None)
    return _card(db, now, text, got, kit, (lead + " That's everything.").strip())


def from_chat(db: Session, settings: Settings, now: datetime, text: str) -> ChatOut | None:
    state = _state(db)
    if state is not None:
        return _interview(db, now, text, state)
    t = _norm(text)
    if _START.match(t):
        _set_state(db, {"step": 0, "facts": {}, "kit": []})
        return _ask(0)
    picked: Picked | None = extract(text)
    if picked is None:
        return None
    f = picked.facts
    check = _weight_note(db, f)
    if check is not None and not check.ok:
        # Too fast to plan: say so, and offer the realistic and stretch targets instead.
        chips = [f"I want to reach {x:g} kg" for x in (check.realistic_kg, check.stretch_kg) if x]
        return ChatOut(
            reply=check.message,
            mood="warning",
            intent="plan_builder",
            source="rules",
            suggestions=chips,
        )
    # A goal, a target weight, days a week or base kit on its own stays the v1.3 edit
    # ("I want to reach 50 kg" sets your target); they ride along with a real plan fact.
    if not picked.specific:
        return None
    lead = check.message if check is not None else "Noted."
    return _card(db, now, text, f, list(picked.equipment_add), lead)


chat.register_plan_builder(from_chat)
