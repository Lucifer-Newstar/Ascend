"""The coaching team (item 13): the main trainer runs the chat and hands a topic to the
specialist who covers it.

    Idris  gym, strength and PRs          Kai   cardio, Muay Thai and martial arts
    Dario  calisthenics                   Tara  mobility, recovery and rest days
    Vera   nutrition and shakes

Iskra is the main trainer by default (Settings "trainer_id" picks another main). Who
speaks is decided after the reply is built, so routing never changes the facts: the
numbers, the safety line and the citations stay exactly as the rules, the knowledge base
or the local AI produced them. Since trainer-answers-v1 the speaker's voice adds an
opener and a sign-off to coaching answers (trainer/voice.py; none on warnings).
Only coaching answers move (a knowledge passage, a coaching help note, a free answer
from the local AI). App questions, tours, greetings,
goal checks and every action card (propose, confirm, undo) stay with the main trainer.

The topic comes from the learned intent label (nutrition_question -> Vera, injury_pain ->
Tara) plus a keyword fallback; a message can also name a specialist ("Kai, how do I...").
When the specialist is the main trainer, or the team is switched off in Settings, the
main trainer answers and there is no handoff line.
"""

from __future__ import annotations

import re
from typing import cast

from sqlalchemy.orm import Session

from app.modules.ml import knowledge
from app.modules.progress import service as progress
from app.modules.trainer import voice
from app.modules.trainer.schemas import ChatOut, TrainerId

TRAINERS: tuple[TrainerId, ...] = ("iskra", "vera", "kai", "dario", "tara", "idris")
NAMES: dict[str, str] = {
    "iskra": "Iskra",
    "vera": "Vera",
    "kai": "Kai",
    "dario": "Dario",
    "tara": "Tara",
    "idris": "Idris",
}
SHE = {"iskra", "vera", "tara"}

# Each specialist's area, as the handoff line says it.
AREAS: dict[str, str] = {
    "idris": "gym, strength and PRs",
    "dario": "calisthenics",
    "kai": "cardio and martial arts",
    "tara": "mobility and recovery",
    "vera": "nutrition",
}

# Keyword fallback: one point per area word in the message.
KEYWORDS: dict[str, re.Pattern[str]] = {
    "vera": re.compile(
        r"\b(protein|calorie|calories|kcal|carbs?|carbohydrates?|macros?|diet|meals?|eat|eating|"
        r"food|foods|shakes?|smoothie|creatine|supplements?|whey|breakfast|lunch|dinner|snacks?|"
        r"vitamins?|fib(re|er)|sugar|rice|dal|idli|dosa|chapati|paneer|eggs?|chicken|banana|"
        r"dates|nuts|milk|vegetarian|vegan|hydration|bulk|bulking|nutrition)\b",
        re.I,
    ),
    "idris": re.compile(
        r"\b(bench|bench press|squats?|deadlifts?|overhead press|ohp|barbell|dumbbells?|"
        r"kettlebells?|gym|lift|lifts|lifting|prs?|1rm|one rep max|rep max|hypertrophy|"
        r"strength|strong|stronger|progressive overload|leg press|lat pulldown|rows?|"
        r"plates?|e1rm|rpe|sets per muscle|reps in reserve|trap bar|hex bar|landmine|pendlay|"
        r"grippers?|grip strength|lifting belts?|lifting straps|rdl|romanian deadlifts?|curls?|"
        r"spotters?|safety bars?|powerlifting|olympic lifts?|snatch|clean and jerk)\b",
        re.I,
    ),
    "dario": re.compile(
        r"\b(calisthenics|push-?ups?|pull-?ups?|chin-?ups?|dips?|muscle-?ups?|handstands?|"
        r"planche|front lever|back lever|l-?sit|pistol squats?|bodyweight|body weight|"
        r"hollow body|planks?|no equipment|without equipment|archer|typewriter|human flag|"
        r"dragon flag|skin the cat|elbow lever|crow pose|wall walks?|shrimp squats?|"
        r"cossack squats?|toes to bar|bear crawls?|parallettes)\b",
        re.I,
    ),
    "kai": re.compile(
        r"\b(cardio|run|runs|running|jog|jogging|sprints?|sprinting|cycling|bike|swim|"
        r"swimming|hiit|stamina|endurance|zone 2|heart rate|vo2|muay thai|boxing|kickboxing|"
        r"mma|martial arts?|karate|taekwondo|bjj|jiu-?jitsu|sparring|shadow ?boxing|punch|"
        r"punches|punching bag|heavy bag|kicks?|skipping|jump rope|footwork|conditioning|"
        r"steps|walking|jab|hooks?|uppercuts?|elbow strikes?|teep|roundhouse|low kicks?|clinch|"
        r"parry|southpaw|orthodox|speed bag|hand wraps?|breakfalls?|ukemi|kata|tabata|"
        r"intervals?|5k|10k|marathon|couch to 5k|rowing|elliptical|stairs|shuttle runs?|"
        r"freestyle|breaststroke|backstroke)\b",
        re.I,
    ),
    "tara": re.compile(
        r"\b(mobility|stretch|stretches|stretching|flexible|flexibility|yoga|foam roll(er|ing)?|"
        r"recovery|recover|recovering|rest days?|sore|soreness|doms|sleep|sleeping|meditat\w*|"
        r"breathing|cool ?down|warm ?up|warming up|tight|stiff|stiffness|posture|pain|hurts?|"
        r"injur\w*|ache|aching|massage|pranayama|anulom|nadi shodhana|bhramari|kapalbhati|"
        r"mindfulness|metta|loving.?kindness|body scan|box breathing|4-7-8|front splits?|"
        r"middle splits?|side splits?|the splits|downward dog|cobra|warrior pose|child'?s pose|"
        r"cat.?cow|pigeon pose|hip flexors?|thoracic|ankle mobility|wrist prep|"
        r"legs up the wall|insomnia|naps?|relax\w*|stress|calm)\b",
        re.I,
    ),
}

# Whose area a cited knowledge passage is in: library passages carry the coach in their id
# (lib:<coach>:<slug>), team notes are grouped by file (ml/knowledge/notes/<stem>.md). Used
# only when the message's own words do not pick one specialist.
NOTE_AREA: dict[str, str] = {
    "cardio_running": "kai",
    "martial_arts": "kai",
    "calisthenics_skills": "dario",
    "gym_strength": "idris",
    "mobility_yoga": "tara",
    "meditation_breathing": "tara",
    "sleep_recovery": "tara",
    "safety": "tara",
    "nutrition_basics": "vera",
    "supplements": "vera",
}

# The learned intent's label is a stronger hint than any one word.
LABEL_HINT: dict[str, str] = {"nutrition_question": "vera", "injury_pain": "tara"}
LABEL_WEIGHT = 2

# Coaching help notes (trainer/kb.py) and who answers them. App how-tos are not here: the
# main trainer answers those.
FAQ_OWNER: dict[str, str] = {
    "protein": "vera",
    "gain_weight": "vera",
    "lose_fat": "vera",
    "water": "vera",
    "pre_workout_food": "vera",
    "post_workout_food": "vera",
    "veg_protein": "vera",
    "creatine": "vera",
    "rice_bulk": "vera",
    "rpe": "idris",
    "e1rm": "idris",
    "deload": "idris",
    "rest_between_sets": "idris",
    "sets_per_muscle": "idris",
    "set_rep": "idris",
    "first_pullup": "dario",
    "pushup_form": "dario",
    "home_workout": "dario",
    "cardio_or_weights": "kai",
    "sore": "tara",
    "warm_up": "tara",
    "sleep": "tara",
    "pain": "tara",
}

# Replies that may move to a specialist: coaching knowledge, not app help or actions.
_TOPICAL_SOURCES = {"knowledge", "ollama"}
_ADDRESS = re.compile(
    r"^\s*(?:@|hey\s+|hi\s+|ask\s+)?(iskra|vera|kai|dario|tara|idris)\b[\s,:!?-]", re.I
)


def main_trainer(db: Session) -> TrainerId:
    value = progress.get_setting(db, "trainer_id", "iskra")
    return cast(TrainerId, value if value in TRAINERS else "iskra")


def team_on(db: Session) -> bool:
    return progress.get_setting(db, "team_handoff", "true") == "true"


def addressed(text: str) -> str | None:
    """A specialist named at the start of the message ("Kai, ...", "ask Vera ...")."""
    m = _ADDRESS.match(text)
    return m.group(1).lower() if m else None


def topic(text: str, label: str | None = None) -> str | None:
    """The specialist whose area the message is in, or None when no area clearly wins."""
    scores = {who: len(rx.findall(text)) for who, rx in KEYWORDS.items()}
    hint = LABEL_HINT.get(label or "")
    if hint:
        scores[hint] += LABEL_WEIGHT
    best = max(scores.values())
    if best == 0:
        return None
    winners = [who for who, s in scores.items() if s == best]
    return winners[0] if len(winners) == 1 else None


_FEDB_GYM = re.compile(r"equipment: (barbell|dumbbell|cable|machine|kettlebells|e-z curl bar)")


def passage_area(passage_id: str) -> str | None:
    """The specialist whose area a knowledge passage is in, from its id, or None.
    An exercise from free-exercise-db goes by what it is (trainer-answers-v1): a stretch
    to Tara, a weights exercise to Idris, a bodyweight one to Dario."""
    kind, _, rest = passage_id.partition(":")
    head = rest.split(":", 1)[0]
    if kind == "lib":
        return head if head in AREAS else None
    if kind == "note":
        return NOTE_AREA.get(head)
    if kind in ("food", "usda"):
        return "vera"
    if kind == "fedb":
        p = knowledge.passage(passage_id)
        text = (p or {}).get("text", "").lower()
        if "stretch" in passage_id.lower() or "smr" in passage_id.lower():
            return "tara"
        if _FEDB_GYM.search(text):
            return "idris"
        if "equipment: body only" in text:
            return "dario"
    return None


def _topical(out: ChatOut) -> bool:
    if out.proposal is not None:
        return False
    if out.source in _TOPICAL_SOURCES:
        return True
    return out.source == "faq" and (out.faq_id or "") in FAQ_OWNER


def specialist_for(text: str, out: ChatOut) -> str | None:
    """Who should give this reply, before the main trainer and the Settings switch apply."""
    if not _topical(out):
        return None
    named = addressed(text)
    if named and named in AREAS:
        return named
    if out.source == "faq":
        return FAQ_OWNER.get(out.faq_id or "")
    who = topic(text, out.intent)
    if who is None and out.citations:
        who = passage_area(out.citations[0].passage_id)
    return who


def handoff_line(main: str, who: str) -> str:
    pronoun = "her" if who in SHE else "him"
    return f"That's {NAMES[who]}'s area ({AREAS[who]}). Over to {pronoun}."


def _voiced(out: ChatOut) -> bool:
    """Replies that get the speaker's voice: coaching answers and clarifying questions.
    App answers, tours, action cards and the "why?" panel stay plain."""
    if out.proposal is not None or out.source == "ollama":
        return False  # the local AI's own words are shown as checked, unchanged
    return _topical(out) or out.intent == "clarify"


def assign(db: Session, text: str, out: ChatOut) -> ChatOut:
    """Stamp who speaks on a finished reply; a specialist's reply carries the main
    trainer's handoff line. The facts are never changed; a coaching answer gets the
    speaker's voice (trainer/voice.py: an opener and a sign-off, no numbers)."""
    main = main_trainer(db)
    who = specialist_for(text, out) if team_on(db) else None
    speaker = main if who is None or who == main else who
    words = voice.speak(speaker, text, out.reply, out.mood) if _voiced(out) else out.reply
    if speaker == main:
        return out.model_copy(update={"speaker": main, "handoff": None, "reply": words})
    return out.model_copy(
        update={
            "speaker": cast(TrainerId, speaker),
            "handoff": handoff_line(main, speaker),
            "reply": words,
        }
    )
