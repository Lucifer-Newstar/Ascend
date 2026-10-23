"""plangen-v1 for the time-based sections (v1.2): cardio, martial arts, flexibility and
meditation. Rule-based and offline, like workout_gen: the built-in program of that section
at your level (beginner, intermediate, expert; the nearest one when there is none) gives
the session templates, and they are spread over the days per week you asked for.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.workouts.programs import PROGRAMS, Day, Program

TIME_SECTIONS = ("cardio", "martial_arts", "flexibility", "meditation")
LEVELS = ("beginner", "intermediate", "expert")
# Spread N days across the week (Monday = 0).
WEEKDAYS: dict[int, tuple[int, ...]] = {
    1: (0,),
    2: (0, 3),
    3: (0, 2, 4),
    4: (0, 1, 3, 5),
    5: (0, 1, 2, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
    7: (0, 1, 2, 3, 4, 5, 6),
}
SECTION_LABEL = {
    "cardio": "Cardio",
    "martial_arts": "Martial Arts",
    "flexibility": "Mobility",
    "meditation": "Calm",
}


@dataclass(frozen=True)
class SectionPlan:
    name: str
    summary: str
    level: str
    days: tuple[Day, ...]
    notes: tuple[str, ...]


def level_for(experience: str) -> str:
    return (
        "expert"
        if experience in ("advanced", "expert")
        else experience
        if experience in LEVELS
        else "beginner"
    )


def template(section: str, level: str) -> Program:
    pool = [p for p in PROGRAMS.values() if p.section_key == section]
    if not pool:
        raise ValueError(f"no programs for section {section}")
    want = LEVELS.index(level)
    return min(
        pool, key=lambda p: (abs(LEVELS.index(p.level) - want) if p.level in LEVELS else 9, p.key)
    )


def generate(section: str, experience: str, days_per_week: int) -> SectionPlan:
    level = level_for(experience)
    base = template(section, level)
    unique: list[Day] = []
    for d in base.days:
        if all(u.slots != d.slots for u in unique):
            unique.append(d)
    n = max(1, min(7, days_per_week))
    days = tuple(
        Day(
            f"d{i + 1}",
            unique[i % len(unique)].name,
            unique[i % len(unique)].focus,
            WEEKDAYS[n][i],
            unique[i % len(unique)].slots,
        )
        for i in range(n)
    )
    notes = [
        f"Built from {base.name} ({base.level}), spread over {n} day{'s' if n != 1 else ''} a week."
    ]
    if base.level != level:
        notes.append(
            f"There is no {level} {SECTION_LABEL[section].lower()} program yet, so this "
            "uses the nearest level."
        )
    return SectionPlan(
        name=f"My {SECTION_LABEL[section]} Plan, {n} days",
        summary=base.summary,
        level=base.level,
        days=days,
        notes=tuple(notes),
    )
