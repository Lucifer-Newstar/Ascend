"""Coach-style answers from knowledge passages, with no AI (trainer-answers-v1).

The local model is optional and off by default, so most knowledge answers are built here
from the passage itself, never from invented text:

1. the direct answer: the passage's one or two sentences that cover the question best
   (team notes lead with their answer, so the first sentence wins a near tie);
2. how to do it: up to four numbered steps from an exercise's own instructions, or one
   more sentence of the note ("Why: ..."), kept short;
3. one personal line from what the app already stores (goal, focus, experience, kit,
   baseline test, the estimated protein target) when it applies to this passage; nothing
   is guessed, and under-18 users never get calorie numbers;
4. the citation stays under the reply (ChatOut.citations), as before.

When retrieval is not sure, `closest()` offers the nearest note as "the closest I have" with
one clarifying question instead of answering with a neighbouring topic, and `clarify()`
asks the one missing thing for a question too vague to answer ("which workout is best?").
Numbers in these replies come from the passage, the user's own data or the engines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.ml import knowledge
from app.modules.progress import service as progress

COMPOSE_VERSION = "trainer-answers-v1"
# Pain words: a pain question keeps the doctor/physio line on every path and gets no cheer.
PAIN = re.compile(
    r"\b(pain|painful|hurts?|hurting|injur\w*|ache|aching|sprain\w*|strain\w*)\b", re.I
)
MAX_STEPS = 4
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_STEPS = re.compile(r"Steps?:\s*(.*)", re.S)
_EQUIP = re.compile(r"equipment: ([a-z ,/-]+)\)", re.I)
_HEAD = re.compile(r"^How to do [^.]*\([^)]*\)\.\s*")


@dataclass(frozen=True)
class Personal:
    """The profile facts a reply may use (all optional; nothing is filled in by guessing)."""

    name: str = ""
    age: int | None = None
    goal: str | None = None
    focus: str | None = None
    experience: str | None = None
    equipment: tuple[str, ...] = ()
    protein_target_g: int | None = None
    baseline_pullups: int | None = None
    baseline_pushups: int | None = None

    @property
    def minor(self) -> bool:
        return self.age is not None and self.age < 18


def personal(db: Session) -> Personal:
    p = progress.get_profile(db)
    if p is None:
        return Personal()
    try:
        protein = progress.energy_for(p).protein_target_g
    except Exception:  # an incomplete profile has no energy targets
        protein = None
    base = p.baseline or {}
    return Personal(
        name=(p.name or "").strip(),
        age=p.age,
        goal=p.goal,
        focus=p.focus,
        experience=p.experience,
        equipment=tuple(p.equipment),
        protein_target_g=protein,
        baseline_pullups=base.get("pullups") or None,
        baseline_pushups=base.get("pushups") or None,
    )


def sentences(text: str) -> list[str]:
    """Whole sentences only: a chunk of a long source (PAG) can start mid-sentence, and
    the library's "Also called" line is a label, not advice."""
    out = [s.strip() for s in _SENT.split(text.strip()) if s.strip()]
    if out and out[0][0].islower():
        out = out[1:]
    return [s for s in out if not s.startswith("Also called:")]


def _clean(text: str) -> str:
    """Drop the source's own bookkeeping that reads badly in a chat bubble."""
    text = re.sub(r"\s*ASCEND food table, approximate home-style values; recipes and oil vary\.",
                  " (approximate, home-style)", text)  # fmt: skip
    return text.strip()


def direct(question: str, text: str, n: int = 2, ranked: bool = False) -> list[str]:
    """The passage's opening answer, in passage order: team notes are written answer-first
    (a ranked pick of "the best sentence" chose caveats over the advice in testing). A
    chunk of a long public-domain document (ranked=True) is not, so there the sentences
    that cover the question best are taken, still in passage order."""
    sents = sentences(_clean(text))
    if not ranked or len(sents) <= n:
        return sents[:n]
    scored = sorted(range(len(sents)), key=lambda i: (-knowledge.share(question, sents[i]), i))
    return [sents[i] for i in sorted(scored[:n])]


def steps(text: str) -> tuple[str, list[str]]:
    """(the line before the steps, the steps) for an exercise passage, else ("", [])."""
    m = _STEPS.search(text)
    if not m:
        return "", []
    lead = _HEAD.sub("", text[: m.start()]).strip()
    body = [s for s in sentences(m.group(1)) if len(s.split()) >= 3]
    return lead, body[:MAX_STEPS]


def _equipment(text: str) -> set[str]:
    m = _EQUIP.search(text)
    return {w.strip().lower() for w in m.group(1).split(",")} if m else set()


_KIT_WORDS = {
    "pullup_bar": {"bar", "pull-up bar", "pole"},
    "rings": {"rings"},
    "dumbbells": {"dumbbell", "dumbbells"},
    "bench": {"bench"},
    "gym": {"barbell", "cable", "machine", "kettlebells", "e-z curl bar", "bands", "other"},
    "none": {"body only", "bodyweight", "none", "mat"},
}
_KIT_NAMES = {
    "pullup_bar": "a pull-up bar",
    "rings": "rings",
    "dumbbells": "dumbbells",
    "bench": "a bench",
    "gym": "a gym",
    "none": "no equipment",
}


def personal_line(me: Personal, passage_id: str, text: str, label: str | None) -> str | None:
    """One line tying the answer to this user, from stored facts only, or None."""
    topic = knowledge.passage_topic(passage_id)
    low = text.lower()
    howto = passage_id.startswith(("fedb:", "lib:"))
    if howto and me.equipment:
        need = _equipment(text) - {"body only", "bodyweight", "none", "mat", ""}
        have = set().union(*(_KIT_WORDS.get(k, set()) for k in me.equipment))
        if "gym" in me.equipment:
            have |= {"barbell", "cable", "machine", "kettlebells", "bands", "dumbbell", "bench"}
        if need and not need & have:
            kit = ", ".join(_KIT_NAMES.get(k, k) for k in me.equipment)
            return (
                f"This one needs {', '.join(sorted(need))}; your kit is {kit}. Ask me for a swap."
            )
    if "pull" in passage_id.lower() and me.baseline_pullups:
        return f"Your baseline test was {me.baseline_pullups} pull-ups; build from there."
    if "push" in passage_id.lower() and me.baseline_pushups:
        return f"Your baseline test was {me.baseline_pushups} push-ups; build from there."
    if howto and me.experience == "beginner":
        return "You're starting out, so use the easiest version and slow, clean reps first."
    if "protein" in low and me.protein_target_g and topic in ("nutrition", None):
        return f"Your estimated protein target is {me.protein_target_g} g a day (on Fuel)."
    if me.goal == "bulk" and topic == "cardio":
        return "You're set to bulk, so eat a bit more on the days you add cardio."
    if me.goal == "bulk" and re.search(r"\b(gain(ing)? weight|weight gain|gain muscle)", low):
        return "That's your goal (bulk); the diet planner can turn this into meals for you."
    if me.goal == "cut" and re.search(r"\b(fat loss|lose weight|losing weight|deficit)", low):
        return "That's your goal (cut); keep the strength work in to hold on to muscle."
    if me.minor and topic in ("gym", "calisthenics"):
        return "Under 18: keep the weights moderate, form first, with someone watching."
    return None


def compose(question: str, hit: knowledge.Passage, me: Personal, label: str | None) -> str:
    """A short coach reply from one passage: direct answer, how-to, one personal line."""
    lead, how = steps(hit.text)
    parts: list[str] = []
    if how:
        name = hit.title[len("How to do ") :] if hit.title.startswith("How to do ") else hit.title
        first = sentences(lead)
        what = first[-1].rstrip(".") if first else ""
        parts.append(
            f"{name}, step by step" + (f" ({what[0].lower()}{what[1:]}):" if what else ":")
        )
        parts.append("\n".join(f"{i}. {s}" for i, s in enumerate(how, 1)))
    else:
        top = direct(question, hit.text, ranked=hit.source in ("pag_2018",))
        parts.append(" ".join(top))
        rest = [s for s in sentences(_clean(hit.text)) if s not in top]
        if rest and len(" ".join(top).split()) < 45:
            tip = max(rest, key=lambda s: knowledge.share(question, s))
            parts.append(tip)
    line = personal_line(me, hit.id, hit.text, label)
    if line and not (me.minor and "kcal" in line):
        parts.append(line)
    return "\n".join(p for p in parts if p)


def closest(question: str, hit: knowledge.Passage) -> tuple[str, list[str]]:
    """'Not sure' reply: the nearest note, named as such, and one clarifying question. The
    note's text is not shown: it is often only a neighbour, and the chip opens it."""
    reply = (
        f'I\'m not sure I have exactly that. The closest note I have is "{hit.title}". '
        "Is that what you meant? If not, tell me a bit more, like your goal or what you've tried."
    )
    name = hit.title[len("How to do ") :] if hit.title.startswith("How to do ") else ""
    chip = f"How do I do {name.lower()}?" if name else f"Tell me about {hit.title.lower()}"
    return reply, [chip]


def vague(question: str) -> bool:
    """Nothing in the question names what it is about ("which workout is the best?")."""
    toks = knowledge.tokens(question)
    return bool(toks) and all(t in knowledge.GENERIC for t in toks)


_FOOD = re.compile(r"\b(eat|eating|diet|food|foods|meal|meals)\b", re.I)
_GOAL_WORDS = {"bulk": "building muscle", "cut": "losing fat", "maintain": "staying fit"}
_WORKOUT_CHIPS = {
    "bulk": "How do I build muscle?",
    "cut": "How do I lose fat?",
    "maintain": "Which program fits my kit?",
}
_FOOD_CHIPS = {
    "bulk": "How do I gain weight?",
    "cut": "How fast should I lose weight?",
    "maintain": "How much protein do I need?",
}


def clarify(question: str, me: Personal) -> tuple[str, list[str]]:
    """One clarifying question for a vague message; the goal on file picks the first chip."""
    goal = _GOAL_WORDS.get(me.goal or "")
    if _FOOD.search(question):
        ask = "What's it for: gaining weight, losing fat or energy for training?"
        chips = dict(_FOOD_CHIPS)
        order = ["How do I gain weight?", "How fast should I lose weight?",
                 "How much protein do I need?"]  # fmt: skip
    else:
        ask = "Best for what: strength, muscle size, fat loss or stamina?"
        chips = dict(_WORKOUT_CHIPS)
        order = ["Which program fits my kit?", "How do I build muscle?", "How do I lose fat?",
                 "How do I build stamina?"]  # fmt: skip
    first = chips.get(me.goal or "")
    if first:
        order = [first, *[o for o in order if o != first]]
    reply = f"Depends on the goal. {ask}"
    if goal:
        reply += f" Your profile says {goal}, so the first option below is for that."
    return reply, order
