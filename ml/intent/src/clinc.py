"""CLINC150 (github.com/clinc/oos-eval, CC BY 3.0) -> ASCEND intents.

CLINC150 is 150 assistant intents written by crowd workers, plus out-of-scope queries.
ASCEND uses it for one thing above all: real people asking things a fitness trainer
should NOT answer (banking, travel, cars, music...), so the router learns to decline.

* MAPPED: a handful of CLINC intents mean the same thing in ASCEND (greeting, thanks,
  "what can I ask you", calories/nutrition facts, cancel).
* DROPPED: assistant-meta intents that could be a real ASCEND request ("set a reminder",
  "change my name", "reset settings", "yes"/"no") or a food question in disguise
  (recipe, meal_suggestion...). Training on them as out_of_scope would teach the router
  to refuse things ASCEND does.
* Everything else, plus CLINC's own `oos` queries, is out_of_scope.

Splits follow CLINC's own train/val/test, so the oos test numbers are on queries never
seen in training.
"""

from __future__ import annotations

import json
from pathlib import Path

MAPPED = {
    "greeting": "greeting",
    "thank_you": "thanks",
    "what_can_i_ask_you": "help",
    "are_you_a_bot": "help",
    "what_is_your_name": "help",
    "calories": "nutrition_question",
    "nutrition_info": "nutrition_question",
    "cancel": "undo_cancel",
}
DROPPED = {
    "reminder",
    "reminder_update",
    "alarm",
    "timer",
    "change_user_name",
    "user_name",
    "reset_settings",
    "change_language",
    "change_volume",
    "change_speed",
    "change_accent",
    "change_ai_name",
    "whisper_mode",
    "sync_device",
    "yes",
    "no",
    "maybe",
    "repeat",
    "goodbye",
    "recipe",
    "meal_suggestion",
    "ingredient_substitution",
    "ingredients_list",
    "cook_time",
    "food_last",
    "shopping_list",
    "shopping_list_update",
    "todo_list",
    "todo_list_update",
    "calendar",
    "calendar_update",
    "measurement_conversion",
    "who_made_you",
    "who_do_you_work_for",
    "how_old_are_you",
    "where_are_you_from",
    "what_are_your_hobbies",
    "do_you_have_pets",
    "meaning_of_life",
    "vaccines",
}


def label(clinc_intent: str) -> str | None:
    if clinc_intent == "oos":
        return "out_of_scope"
    if clinc_intent in MAPPED:
        return MAPPED[clinc_intent]
    if clinc_intent in DROPPED:
        return None
    return "out_of_scope"


def load(path: Path, per_intent: int = 12) -> dict[str, list[tuple[str, str]]]:
    """{"train"|"val"|"test": [(text, ascend_intent)]}, at most `per_intent` in-scope
    examples per CLINC intent and split (all oos queries are kept)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[tuple[str, str]]] = {}
    for split in ("train", "val", "test"):
        rows: list[tuple[str, str]] = []
        seen: dict[str, int] = {}
        for text, intent in data[split]:
            lab = label(intent)
            if lab is None:
                continue
            cap = per_intent * (3 if intent in MAPPED else 1)
            if seen.get(intent, 0) >= cap:
                continue
            seen[intent] = seen.get(intent, 0) + 1
            rows.append((text, lab))
        rows += [(text, "out_of_scope") for text, _ in data[f"oos_{split}"]]
        out[split] = rows
    return out
