"""Weak labels for Fitness Stack Exchange question titles (labelling functions).

These are RULES, not people: each title gets the first label whose rule fires, in the
order below, from its tags plus words in the title. They are good enough to train a
router, not good enough to report accuracy on, which is why the reported numbers come
from (a) the hand-checked rows in labels/se_handchecked.csv and (b) the external
real-question set (see DATA_CARD.md). `rule` records which function fired, so a wrong
rule can be traced and fixed.
"""

from __future__ import annotations

import re

PAIN_TAGS = {
    "pain", "back-pain", "knee-pain", "shoulder-pain", "lower-back-pain", "tendinitis",
    "sprain", "physical-therapy", "rehabilitation",
}
NUTRITION_TAGS = {
    "diet", "nutrition", "calories", "protein", "supplements", "food", "carbohydrate",
    "protein-shakes", "creatine", "ketogenic-diet", "eating-habits", "daily-caloric-intake",
    "vitamins", "caffeine", "hydration", "water", "pre-workout", "post-workout-meal",
    "fasting", "intermittent-fasting", "vegetarian", "vegan", "macros", "sugar", "alcohol",
}
HOWTO_TAGS = {"exercise-technique", "form"}
MOTIVATION_TAGS = {"motivation", "discipline", "habits"}

_PAIN = re.compile(
    r"\b(pain|painful|hurts?|hurting|injur\w*|sprain\w*|strain(ed)?|tendinit\w*|tendon\w*|"
    r"ache|aching|torn|tear|swollen|swelling|numb\w*|tingl\w*|physio\w*|doctor|surgery|"
    r"hernia|sciatica|shin splints?|plantar|clicking|popping|dislocat\w*|fractur\w*|"
    r"rotator cuff|bursitis|impingement)\b",
    re.I,
)
_FOOD = re.compile(
    r"\b(eat\w*|ate|food\w*|diet\w*|meal\w*|protein|calori\w*|kcal|carb\w*|supplement\w*|"
    r"creatine|whey|vitamin\w*|drink\w*|water|coffee|caffeine|sugar|breakfast|lunch|dinner|"
    r"snack\w*|nutrition\w*|nutrient\w*|fasting|macros?|keto\w*|vegan|vegetarian|"
    r"milk|eggs?|rice|chicken|fruit\w*|bcaa\w*|shake\w*|bulk(ing)? diet|fat intake|"
    r"cholesterol|sodium|salt|alcohol|beer|hungry|hunger|appetite)\b",
    re.I,
)
_HOWTO = re.compile(
    r"(\bhow (to|do i|do you|should i|can i) (do|perform|properly|correctly|execute|"
    r"get better at|learn|achieve|master|start doing)\b|\bproper (form|technique|way)\b|"
    r"\bcorrect (form|technique|way)\b|\btechnique\b|\bform\b.*\b(squat|deadlift|press|row|"
    r"curl|push-?ups?|pull-?ups?|lunge|dip)|\bwhat muscles? (does|do|is|are)\b|"
    r"\bmuscles? (worked|used|targeted)\b|\b(alternative|substitute|replacement)s? (to|for)\b|"
    r"\b(exercise|exercises|movement|workout)s? (for|to target|to work|that target)\b|"
    r"\bhow to (do|get) (a |my )?(first )?(pull-?up|push-?up|chin-?up|muscle-?up|dip|"
    r"handstand|pistol|squat|l-?sit|plank|front lever|back lever|planche)s?\b|"
    r"\bgrip\b|\bbreathing (during|while|when)\b)",
    re.I,
)
_MOTIVATION = re.compile(
    r"\b(motivat\w*|lazy|laziness|discipline|consisten\w*|stick (to|with) (it|a|my)|"
    r"give up|giving up|bored|boring|willpower|procrastinat\w*|keep going)\b",
    re.I,
)
_PLAN = re.compile(
    r"\b(good|best|beginner'?s?|recommend\w*|suggest\w*|which|what)\b.*\b(routine|program|"
    r"programme|plan|split|schedule)\b|\b(routine|program|plan|split) for (a )?(beginner|"
    r"me|skinny|home|weight loss|muscle gain|mass)\b|\b(create|design|make|build) (a|my) "
    r"(own )?(routine|program|plan|workout)\b",
    re.I,
)

ORDER = ("injury", "nutrition", "howto", "motivation", "plan", "default")


def label(title: str, tags: list[str]) -> tuple[str, str]:
    """(intent, rule) for one Stack Exchange question."""
    tagset = set(tags)
    t = title or ""
    # A tag alone ("injury", "injury-prevention") is not enough: many of those titles ask
    # how to warm up or train around something. A pain tag or a pain word in the title is.
    if _PAIN.search(t) or tagset & PAIN_TAGS:
        return "injury_pain", "injury"
    if _FOOD.search(t) and (tagset & NUTRITION_TAGS or not (_HOWTO.search(t) or tagset & HOWTO_TAGS)):
        return "nutrition_question", "nutrition"
    if _HOWTO.search(t) or tagset & HOWTO_TAGS:
        return "exercise_howto", "howto"
    if _MOTIVATION.search(t) or tagset & MOTIVATION_TAGS:
        return "motivation", "motivation"
    if _PLAN.search(t):
        return "plan_request", "plan"
    return "training_question", "default"
