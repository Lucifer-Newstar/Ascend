# ruff: noqa: E501  (the phrase patterns read best one rule per line)
"""Rules that read an edit from a chat line (v1.3 wave 2): profile, kit, settings, plan.

parse_edit(text) -> (kind, params) or None. Only clear commands match ("change my goal to
bulk", "I have a bench", "switch to lbs", "swap bench press for push-ups"); a question is
never an edit. The service still validates every value and the user confirms the card.
"""

from __future__ import annotations

import re
from typing import Any

Hit = tuple[str, dict[str, Any]]

DAYS = {d: i for i, d in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday",
                                     "saturday", "sunday"))}  # fmt: skip
DAY_ABBR = {"mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3,
            "fri": 4, "sat": 5, "sun": 6}  # fmt: skip
_DAY = r"(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)(?:day|nesday|sday|urday|rsday)?s?"

KIT = [
    (r"(?:a )?(?:pull ?-?up|chin ?-?up|doorway|door) bars?|(?:a )?bar", "pullup_bar"),
    (r"(?:gymnastic |gym )?rings", "rings"),
    (r"(?:a pair of |some |a set of |two |2 |one |a |an )?(?:adjustable )?(?:dumb ?bells?|dbs?)", "dumbbells"),
    (r"(?:a |an )?(?:flat |adjustable |weight |workout )?bench", "bench"),
    (r"(?:a )?(?:gym(?: membership)?|full gym)", "gym"),
]  # fmt: skip
GOALS = {
    "bulk": "bulk", "bulking": "bulk", "gain weight": "bulk", "gain muscle": "bulk",
    "build muscle": "bulk", "put on weight": "bulk", "weight gain": "bulk",
    "cut": "cut", "cutting": "cut", "lose fat": "cut", "lose weight": "cut", "fat loss": "cut",
    "weight loss": "cut", "maintain": "maintain", "maintenance": "maintain",
    "stay the same": "maintain",
}  # fmt: skip
THEMES = ("dark", "light", "system", "shadow", "crimson", "frost", "emerald", "solar")
TRAINERS = ("iskra", "vera", "kai", "dario")


def _clean(text: str) -> str:
    t = text.lower().strip().replace("\u2019", "'")
    t = re.sub(r"[.!]+$", "", t)
    t = re.sub(r"^(?:please |pls |can you |could you |hey |ok |okay )+", "", t)
    t = re.sub(r" (?:please|pls|for me)$", "", t)
    return re.sub(r"\s+", " ", t).strip()


def weekday(word: str | None) -> int | None:
    if not word:
        return None
    w = word.lower().rstrip("s")
    if w in DAYS:
        return DAYS[w]
    m = re.match(_DAY, w)
    return DAY_ABBR.get(m.group(1)) if m else None


def _kit(phrase: str) -> list[str] | None:
    """ "a bench and 2 dumbbells" -> ["bench", "dumbbells"]; None if any part isn't kit."""
    out: list[str] = []
    for part in re.split(r"\s*(?:,|\band\b|&|\+)\s*", phrase):
        part = re.sub(
            r"^(?:\d+(?:\.\d+)?\s?(?:kg|kgs)?\s?|(?:one|two|three|four|a pair of|pair of) |a |an |some |my |the |any |x\s?)+",
            "",
            part.strip(),
        )
        part = re.sub(r"\s(?:of )?\d+\s?(?:kg|kgs)$", "", part)
        if not part:
            continue
        hit = next((c for rx, c in KIT if re.fullmatch(rx, part)), None)
        if hit is None:
            return None
        if hit not in out:
            out.append(hit)
    return out or None


def _cm(value: str) -> float | None:
    m = re.fullmatch(r"(\d)\s?(?:'|ft|feet|foot)\s?(\d{1,2})?\s?(?:\"|in|inch|inches)?", value)
    if m:
        return round((int(m.group(1)) * 12 + int(m.group(2) or 0)) * 2.54, 1)
    m = re.fullmatch(r"(\d{2,3}(?:\.\d)?)\s?(?:cm|cms)?(?: tall)?", value)
    return float(m.group(1)) if m else None


def _kg(value: str) -> float | None:
    m = re.fullmatch(r"(\d{2,3}(?:\.\d)?)\s?(?:kg|kgs|kilos?)?", value)
    return float(m.group(1)) if m else None


def _profile(t: str) -> Hit | None:
    m = re.fullmatch(
        r"(?:set|change|update|make|put) my (age|height|weight|body ?weight|goal|target weight|"
        r"goal weight|name|activity(?: level)?|experience(?: level)?|level) (?:to|as|=) ?(.+)",
        t,
    ) or re.fullmatch(
        r"my (age|height|goal|target weight|goal weight|name|activity(?: level)?) is (?:now )?(.+)",
        t,
    )
    if m:
        field, value = m.group(1), m.group(2).strip()
        if field == "age":
            n = re.fullmatch(r"(\d{1,3})(?: years?(?: old)?| yrs?| yo)?", value)
            return ("update_profile", {"field": "age", "value": int(n.group(1))}) if n else None
        if field == "height":
            cm = _cm(value)
            return ("update_profile", {"field": "height_cm", "value": cm}) if cm else None
        if field in ("weight", "body weight", "bodyweight"):
            kg = _kg(value)
            return ("update_profile", {"field": "weight_kg", "value": kg}) if kg else None
        if field in ("target weight", "goal weight"):
            kg = _kg(value)
            return ("update_profile", {"field": "target_weight_kg", "value": kg}) if kg else None
        if field == "goal":
            g = GOALS.get(re.sub(r"^(?:to |a )", "", value))
            return ("update_profile", {"field": "goal", "value": g}) if g else None
        if field == "name":
            return ("update_profile", {"field": "name", "value": value.title()[:80]})
        if field.startswith("activity"):
            a = value.replace(" ", "_").replace("very_active", "very_active")
            return ("update_profile", {"field": "activity", "value": a})
        lvl = value.replace("an ", "").replace("a ", "")
        return ("update_profile", {"field": "experience", "value": lvl})
    m = re.fullmatch(r"i(?: am|'m) (\d{2}) (?:years? old|yrs?(?: old)?|yo)", t)
    if m:
        return "update_profile", {"field": "age", "value": int(m.group(1))}
    m = re.fullmatch(
        r"i(?: am|'m) (\d(?:'|ft| ft| feet)\s?\d{0,2}(?:\"| ?in(?:ches)?)?|\d{3} ?cm)(?: tall)?", t
    )
    if m and _cm(m.group(1)):
        return "update_profile", {"field": "height_cm", "value": _cm(m.group(1))}
    m = re.fullmatch(r"(?:call me|my name is) ([a-z][a-z .'-]{0,40})", t)
    if m:
        return "update_profile", {"field": "name", "value": m.group(1).title()}
    m = re.fullmatch(r"i(?: am|'m) (?:a |an )?(beginner|intermediate|advanced)(?: lifter)?", t)
    if m:
        return "update_profile", {"field": "experience", "value": m.group(1)}
    m = re.fullmatch(
        r"(?:i want to |i wanna |i'd like to )?(?:reach|get to|hit|be) (\d{2,3}(?:\.\d)?) ?(?:kg|kgs|kilos?)"
        r"(?: body ?weight)?|my (?:target|goal) is (\d{2,3}(?:\.\d)?) ?(?:kg|kgs|kilos?)",
        t,
    )  # fmt: skip
    if m:
        return "update_profile", {
            "field": "target_weight_kg",
            "value": float(m.group(1) or m.group(2)),
        }
    m = re.fullmatch(
        r"(?:i want to |i wanna )(bulk|cut|gain weight|gain muscle|build muscle|lose fat|lose weight|maintain)(?: now)?",
        t,
    )
    if m:
        return "update_profile", {"field": "goal", "value": GOALS[m.group(1)]}
    return None


def _setting(t: str) -> Hit | None:
    m = re.fullmatch(
        r"(?:switch|change|set)?(?: the| my)? ?(?:units? )?(?:to |in )?(kg|kgs|kilos?|metric|lbs?|pounds|imperial)"
        r"(?: please)?|use (kg|kilos|metric|lbs?|pounds|imperial)(?: units)?",
        t,
    )  # fmt: skip
    if m and re.match(r"(?:switch|change|set|use|to)\b", t):
        word = m.group(1) or m.group(2)
        return "update_setting", {
            "key": "units",
            "value": "imperial" if word[0] in "lpi" else "metric",
        }
    m = re.fullmatch(
        r"(?:switch to |use |turn on |set (?:the )?theme to |change (?:the )?theme to |enable )"
        r"(" + "|".join(THEMES) + r")(?: mode| theme)?|(" + "|".join(THEMES) + r") (?:mode|theme)(?: on| please)?",
        t,
    )  # fmt: skip
    if m:
        return "update_setting", {"key": "theme", "value": m.group(1) or m.group(2)}
    toggles = {
        "reminders?|notifications?|nudges?": "reminders",
        "(?:the )?(?:local )?ai|the coach model|ollama": "ai_enabled",
        "animations?|motion": "reduce_motion",
        "background(?: art)?": "background_art",
    }
    for words, key in toggles.items():
        m = re.fullmatch(
            rf"(turn|switch) (on|off) (?:the |my )?(?:{words})|(enable|disable|stop|mute|unmute) (?:the |my |all )?(?:{words})|(?:{words}) (on|off)",
            t,
        )
        if not m:
            m = re.fullmatch(rf"(no more) (?:{words})", t)
        if m:
            on = any(w in ("on", "enable", "unmute") for w in m.groups() if w)
            if key == "reduce_motion":
                return "update_setting", {"key": key, "value": not on}
            if key == "background_art":
                return "update_setting", {"key": key, "value": "on" if on else "off"}
            return "update_setting", {"key": key, "value": on}
    if re.fullmatch(r"(?:reduce|less) motion|no animations?", t):
        return "update_setting", {"key": "reduce_motion", "value": True}
    m = re.fullmatch(r"(hide|show) (?:my |the )?calories", t)
    if m:
        return "update_setting", {"key": "hide_calories", "value": m.group(1) == "hide"}
    m = re.fullmatch(
        r"(?:switch|change) (?:my )?trainer to (" + "|".join(TRAINERS) + r")|(?:i want |make )?("
        + "|".join(TRAINERS) + r") (?:as|to be) my trainer",
        t,
    )  # fmt: skip
    if m:
        return "update_setting", {"key": "trainer_id", "value": m.group(1) or m.group(2)}
    m = re.fullmatch(r"set (?:my )?sessions(?: per week)? to (\d)", t)
    if m:
        return "update_setting", {"key": "sessions_per_week", "value": int(m.group(1))}
    return None


def _equipment(t: str) -> Hit | None:
    if re.fullmatch(
        r"i (?:have|got) no (?:equipment|kit|gear)|i don'?t have any (?:equipment|kit|gear)|no equipment",
        t,
    ):
        return "set_equipment", {
            "add": ["none"],
            "remove": ["pullup_bar", "rings", "dumbbells", "bench", "gym"],
        }
    m = re.fullmatch(
        r"(?:i (?:now )?(?:have|got|bought|own)|i've got|add|i just (?:got|bought)|i joined) (.+?)"
        r"(?: (?:now|at home|too|as well))?(?: to my (?:kit|equipment|gear|loadout))?",
        t,
    )  # fmt: skip
    if m:
        kit = _kit(m.group(1))
        if kit:
            return "set_equipment", {"add": kit, "remove": []}
    m = re.fullmatch(
        r"(?:i (?:don'?t|do not|no longer) have|remove|i sold|i lost|i gave away) (.+?)"
        r"(?: (?:anymore|any more|now))?(?: from my (?:kit|equipment|gear|loadout))?",
        t,
    )  # fmt: skip
    if m:
        kit = _kit(m.group(1))
        if kit:
            return "set_equipment", {"add": [], "remove": kit}
    return None


_PLAN = r"(?: (?:in|from|to) my (?:plan|program|programme|workouts?|routine|split))"


def _plan(t: str) -> Hit | None:
    on = rf"(?: on {_DAY})?"
    m = re.fullmatch(rf"(?:make|set|change) (.+?) (?:to )?(\d{{1,2}}) sets{_PLAN}?", t)
    if m:
        return "edit_plan", {"op": "sets", "exercise": m.group(1), "sets": int(m.group(2))}
    m = re.fullmatch(
        rf"(?:make|set|change) (.+?) (?:to )?(\d{{1,3}}) ?(?:-|to|\u2013) ?(\d{{1,3}}) (?:reps|seconds|secs?|s){_PLAN}?",
        t,
    )
    if m:
        return "edit_plan", {
            "op": "reps",
            "exercise": m.group(1),
            "rep_low": int(m.group(2)),
            "rep_high": int(m.group(3)),
        }
    m = re.fullmatch(
        rf"(?:swap|replace|switch|change|sub|substitute) (.+?) (?:for|with|to|by) (.+?){_PLAN}?{on}",
        t,
    )
    if m and not re.search(r"\b(?:goal|units?|theme|trainer|name|age|height|weight)\b", m.group(1)):
        return "edit_plan", {
            "op": "swap",
            "exercise": m.group(1),
            "new_exercise": m.group(2),
            "weekday": weekday(m.group(3)),
        }
    m = re.fullmatch(rf"(?:remove|drop|take out|delete|skip) (.+?){_PLAN}{on}", t)
    if m:
        return "edit_plan", {"op": "remove", "exercise": m.group(1), "weekday": weekday(m.group(2))}
    m = re.fullmatch(rf"add (?:(\d) sets? of )?(.+?){_PLAN}{on}", t)
    if m:
        return "edit_plan", {
            "op": "add",
            "exercise": m.group(2),
            "sets": int(m.group(1) or 3),
            "weekday": weekday(m.group(3)),
        }
    m = re.fullmatch(
        rf"move (?:my )?(.+?)(?:'s)?(?: session| workout| training| day)? (?:to|onto) {_DAY}", t
    )
    if m:
        src = m.group(1).strip()
        wd = weekday(src.split()[0]) if src.split() else None
        if wd is not None and len(src.split()) == 1:
            return "edit_plan", {"op": "move_day", "weekday": wd, "to_weekday": weekday(m.group(2))}
        return "edit_plan", {"op": "move_day", "day": src, "to_weekday": weekday(m.group(2))}
    return None


def parse_edit(text: str) -> Hit | None:
    """The edit a chat line asks for, or None."""
    if "?" in text:
        return None
    t = _clean(text)
    if not t or len(t) > 120:
        return None
    for rule in (_setting, _profile, _equipment, _plan):
        hit = rule(t)
        if hit is not None:
            return hit
    return None
