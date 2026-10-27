"""Trainer voices (trainer-answers-v1): each trainer says a coaching answer their own way.

The facts never change with the speaker: the reply is built first (rules, help note,
knowledge passage or local AI, with the number guard and the safety line), then the voice
adds one short opener and, on a short reply, one sign-off. Voice lines carry no numbers,
no body comments, no loss or guilt words and no medical claims, and a warning reply (pain,
an unrealistic goal) gets no voice at all, so the safety line stays first and plain.

The voices follow each trainer's card in the picker (apps/desktop/src/lib/trainer.ts ROSTER)
and the persona rules in docs/research/v8-trainer-persona.md section 2.2:

    Iskra  stern drill instructor: fact first, calls the user "Hunter"
    Vera   playful hype coach: teasing but kind, keeps it light
    Kai    high-energy hype-man: big cheers, straight talk
    Dario  calm strategist: quiet, tactical, the long game
    Tara   calm mobility coach: unhurried and warm, breath first
    Idris  steady strength coach: patient and exact
"""

from __future__ import annotations

import zlib

from app.modules.trainer.compose import PAIN

VOICE_VERSION = "voice-v1"
CLOSER_MAX_WORDS = 70

OPENERS: dict[str, tuple[str, ...]] = {
    "iskra": ("Hunter, straight answer.", "Listen up, Hunter.", "Facts first, Hunter."),
    "vera": ("Ooh, good one!", "Okay, fuel talk!", "Love this question."),
    "kai": ("Let's go!", "Love the energy!", "Alright, fighter!"),
    "dario": ("Here's the plan.", "Let's think long game.", "Let's be tactical."),
    "tara": ("Gently now.", "Let's take this slowly.", "Breathe first, then this."),
    "idris": ("Do it right.", "Here's the exact version.", "Steady and precise."),
}
CLOSERS: dict[str, tuple[str, ...]] = {
    "iskra": ("Your call, Hunter.", "Earn it.", "Log it when it's done."),
    "vera": ("Easy wins, promise.", "Keep it fun and keep moving!", "Snack smart, train happy."),
    "kai": ("Stay light on your feet!", "Big energy, clean form!", "Now go move!"),
    "dario": ("Small steps compound.", "Patience wins this one.", "Master the basics first."),
    "tara": ("Listen to your body.", "Ease in, no rush.", "Calm and steady."),
    "idris": ("Form before load.", "Heavy days done right, light days respected.",
              "Patience under the bar."),
}  # fmt: skip


def _pick(key: str, options: tuple[str, ...], salt: str) -> str:
    return options[zlib.crc32(f"{salt}:{key}".encode()) % len(options)]


def speak(who: str, question: str, reply: str, mood: str) -> str:
    """The reply in this trainer's voice: an opener, the reply, and a sign-off when short."""
    if mood == "warning" or who not in OPENERS or not reply.strip() or PAIN.search(question):
        return reply
    # A "not sure" reply is said plainly: it is a question back, not a coaching answer.
    if reply.startswith("I'm not sure"):
        return reply
    out = f"{_pick(question, OPENERS[who], 'open')} {reply}"
    if len(reply.split()) <= CLOSER_MAX_WORDS:
        out += "\n" + _pick(question, CLOSERS[who], "close")
    return out
