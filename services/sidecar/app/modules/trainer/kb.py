"""trainer-kb-v1: the trainer's local help notes, answered without any AI.

Each entry has the words that point to it, a plain answer and, where it helps, the
section the trainer can tour. Matching is deterministic word overlap (no model), so basic
questions work on any PC, offline, instantly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KB_VERSION = "trainer-kb-v1"

# Section id -> words that name it (the tour and "open ..." use these).
SECTIONS: dict[str, tuple[str, ...]] = {
    "dashboard": ("today", "dashboard", "home", "quest", "quests", "rings", "main page"),
    "workout": ("train", "workout", "logger", "log a set", "session", "gym page"),
    "library": ("exercises", "exercise library", "library"),
    "skills": ("skills", "skill tree", "skill trees", "calisthenics"),
    "progress": (
        "progress",
        "weight chart",
        "body",
        "measurements",
        "muscle map",
        "weekly review",
        "deload",
    ),
    "diet": ("fuel", "diet", "food", "meals", "nutrition", "calories"),
    "planner": ("planner", "plan builder", "plans", "ai planner"),
    "profile": ("profile", "gallery", "progress photos", "achievements", "avatar"),
    "history": ("history", "past workouts", "calendar"),
    "data": ("import", "export", "backup", "data page"),
    "settings": ("settings", "preferences", "options"),
}

SECTION_TITLES: dict[str, str] = {
    "dashboard": "Today",
    "workout": "Train",
    "library": "Exercises",
    "skills": "Skills",
    "progress": "Progress",
    "diet": "Fuel",
    "planner": "Planner",
    "profile": "Profile",
    "history": "History",
    "data": "Import & export",
    "settings": "Settings",
}


@dataclass(frozen=True)
class Entry:
    id: str
    question: str
    keys: tuple[str, ...]
    answer: str
    section: str | None = None


ENTRIES: tuple[Entry, ...] = (
    Entry(
        "log_set",
        "How do I log a set?",
        ("log", "set", "sets", "reps", "record", "logger"),
        "Open Train, pick or search an exercise, type the weight and reps and press Enter. "
        "Each set is saved the moment you enter it; the suggestion card shows the next target.",
        "workout",
    ),
    Entry(
        "xp",
        "How does XP work?",
        ("xp", "experience", "points", "level", "levels"),
        "You earn XP for logged sets, finished sessions, meals, check-ins and quests. There is a "
        "daily cap so farming doesn't pay; levels and ranks come from your total XP.",
        "dashboard",
    ),
    Entry(
        "rank",
        "What are ranks?",
        ("rank", "ranks", "e rank", "s rank", "hunter rank"),
        "Ranks go E, D, C, B, A, S as your level rises. They are cosmetic titles for consistency; "
        "they never change your training numbers.",
        "dashboard",
    ),
    Entry(
        "quests",
        "What are daily quests?",
        ("quest", "quests", "daily", "mission"),
        "Each day you get a short quest list sized to your recovery and check-in: a training "
        "item, a nutrition item and small habits. Finish them for XP.",
        "dashboard",
    ),
    Entry(
        "streak",
        "How do streaks work?",
        ("streak", "streaks", "freeze", "freezes"),
        "Any day you train or log counts toward your streak. Streak freezes, earned over time, "
        "cover a missed day automatically.",
        "dashboard",
    ),
    Entry(
        "boss",
        "What is the boss raid?",
        ("boss", "raid", "bosses", "weekly boss"),
        "Each Monday a boss appears with HP equal to about a week of your training. Every set "
        "you log is one hit. Beat it by Sunday for bonus XP and a title; missing it costs "
        "nothing.",
        "dashboard",
    ),
    Entry(
        "skills",
        "How do skill trees work?",
        (
            "skill",
            "skills",
            "tree",
            "unlock",
            "progression",
            "calisthenics",
            "muscle up",
            "handstand",
            "lever",
            "planche",
        ),
        "Each skill is a ladder of progressions. A step unlocks when your logged sets meet its "
        "criteria (for example 3x8 of the step before). Train a step from the Skills page.",
        "skills",
    ),
    Entry(
        "custom_skill",
        "Can I add my own skill?",
        ("own skill", "custom skill", "add skill", "create skill", "new skill"),
        "Yes. On Skills choose Add your own skill, name it, pick its exercises in order and set "
        "the sets and reps (or seconds) that unlock each step.",
        "skills",
    ),
    Entry(
        "why_target",
        "Why is my target this weight?",
        ("why", "target", "suggestion", "progression", "next weight", "load"),
        "Targets come from the progression engine: it reads your last sessions of that "
        "exercise, your RPE and your recovery, then adds load or reps. Press Why? on any target "
        "to see the exact numbers.",
        "workout",
    ),
    Entry(
        "rpe",
        "What is RPE?",
        ("rpe", "effort", "rir", "reps in reserve"),
        "RPE is how hard a set felt from 1 to 10. RPE 8 means you had about two reps left. "
        "Logging it lets the engine pick better targets.",
        "workout",
    ),
    Entry(
        "e1rm",
        "What is e1RM?",
        ("e1rm", "1rm", "one rep max", "max"),
        "e1RM is your estimated one-rep max from a set's weight and reps (the Epley formula). "
        "PRs are tracked on it, so a heavier triple can beat an old single.",
        "progress",
    ),
    Entry(
        "pr",
        "How are PRs counted?",
        ("pr", "prs", "personal record", "record"),
        "A PR is a new best e1RM on an exercise. You get XP for it, the trainer calls it out and "
        "you can share it as a card.",
        "progress",
    ),
    Entry(
        "deload",
        "What is a deload?",
        ("deload", "rest week", "tired", "fatigue"),
        "A deload is a lighter week (about half the sets at RPE 7) when the engine sees your "
        "performance and recovery slipping. It lets fatigue drop so progress resumes.",
        "progress",
    ),
    Entry(
        "recovery",
        "What do the muscle colours mean?",
        ("muscle", "map", "colour", "color", "recovery", "red", "green", "sore", "soreness"),
        "The map shows each muscle's weekly load and recovery: under-trained, in the optimal "
        "range, still recovering, or over the weekly range. Click a muscle for its history.",
        "progress",
    ),
    Entry(
        "checkin",
        "What is the morning check-in?",
        ("check in", "checkin", "readiness", "sleep", "energy", "mood"),
        "Rate sleep, energy, soreness and mood in a few taps. Your readiness score adjusts the "
        "day's training quest.",
        "dashboard",
    ),
    Entry(
        "tdee",
        "How are my calories calculated?",
        ("tdee", "calories", "kcal", "maintenance", "bmr", "calorie", "target"),
        "Your calorie target starts from the Mifflin-St Jeor equation and your activity level, "
        "then adapts to your real weigh-ins and logged meals over a few weeks.",
        "diet",
    ),
    Entry(
        "protein",
        "How much protein should I eat?",
        ("protein", "grams", "macros", "macro"),
        "ASCEND targets 1.6-2.2 g per kg of body weight depending on your goal, within the "
        "1.4-2.0 g/kg range sports nutrition research recommends for people who train.",
        "diet",
    ),
    Entry(
        "log_meal",
        "How do I log food?",
        ("log food", "meal", "meals", "food", "eat", "ate", "katori", "portion"),
        "On Fuel, search a food and pick the portion (pieces, katori, tbsp). Indian portions are "
        "built in; totals update straight away.",
        "diet",
    ),
    Entry(
        "weigh_in",
        "How do I log my weight?",
        ("weigh", "weight", "weigh in", "scale", "body weight"),
        "On Progress, add a weigh-in. The chart shows a smoothed trend so daily water swings "
        "don't fool you; weigh in at the same time each morning.",
        "progress",
    ),
    Entry(
        "eta",
        "When will I reach my goal weight?",
        ("goal weight", "eta", "reach", "how long"),
        "Progress shows an estimate from your weight trend, with a range and a confidence. It is "
        "an estimate, not a promise; it sharpens with more weigh-ins.",
        "progress",
    ),
    Entry(
        "programs",
        "Which program should I follow?",
        ("program", "programme", "split", "routine", "ppl", "upper lower", "full body"),
        "Train has four built-in programs (full body, upper/lower, push/pull/legs, home). Or ask "
        "me for a custom plan and the planner builds one around your goal, equipment and days.",
        "workout",
    ),
    Entry(
        "planner",
        "How does the AI planner work?",
        ("planner", "custom plan", "ai plan", "make a plan", "build a plan"),
        "The planner drafts a workout program or a 7-day meal plan from your profile. Rules make "
        "the numbers and check your goal; the local AI only rewords the summary. You review, "
        "edit and save.",
        "planner",
    ),
    Entry(
        "import",
        "Can I import my old data?",
        ("import", "strong", "hevy", "csv", "old data", "existing data", "transfer"),
        "Yes. Import & export reads Strong and Hevy CSV exports and ASCEND backups. You get a "
        "dry-run report before anything is written.",
        "data",
    ),
    Entry(
        "backup",
        "How do backups work?",
        ("backup", "backups", "restore", "safe", "lose"),
        "ASCEND keeps a daily backup automatically (two weeks). You can make one any time and "
        "restore from Settings; a restore backs up the current data first.",
        "data",
    ),
    Entry(
        "export",
        "How do I export my data?",
        ("export", "json", "download", "spreadsheet"),
        "Import & export saves everything as JSON or your workouts and meals as CSV.",
        "data",
    ),
    Entry(
        "privacy",
        "Is my data private?",
        (
            "privacy",
            "private",
            "cloud",
            "online",
            "upload",
            "uploaded",
            "internet",
            "account",
            "telemetry",
        ),
        "Everything stays on this PC: no account, no cloud, no telemetry. The only network use "
        "is the optional exercise lookup you switch on, and the share links you choose to open.",
        "settings",
    ),
    Entry(
        "ai",
        "Do I need the AI?",
        ("ai", "ollama", "qwen", "model", "llm", "offline ai"),
        "No. Everything works without it: I answer from my notes and the planner uses rules. "
        "With Ollama installed, a local model rewords answers and plans on your PC. Settings > "
        "AI setup checks your PC and recommends a model.",
        "settings",
    ),
    Entry(
        "photos",
        "How do progress photos work?",
        ("photo", "photos", "picture", "pictures", "gallery", "selfie"),
        "On Profile add a photo for any date. They stay in your data folder, are included in "
        "backups and can be compared side by side. I remind you once a month.",
        "profile",
    ),
    Entry(
        "photo_ai",
        "Can the AI rate my physique?",
        ("physique", "body fat", "analyse photo", "analyze photo", "rate my", "photo feedback"),
        "With the optional vision model installed, I can compare two of your photos and comment "
        "on visible changes like definition and posture. It never estimates body fat and it is "
        "not medical advice.",
        "profile",
    ),
    Entry(
        "share",
        "Can I share my achievements?",
        ("share", "post", "instagram", "twitter", "x", "social"),
        "Yes. PRs, unlocked skills, streak milestones, finished programs, rank-ups and boss wins "
        "get a Share button: an image card plus a caption. X opens with the post ready; for "
        "Instagram the image is saved and the caption copied.",
        "profile",
    ),
    Entry(
        "trainer_choice",
        "Can I change my trainer?",
        ("change trainer", "switch trainer", "another trainer", "trainers", "trainer"),
        'Yes, pick any trainer in Settings or say "change trainer". All of us read the same '
        "numbers; only the voice changes.",
        "settings",
    ),
    Entry(
        "units",
        "Can I use pounds?",
        ("pounds", "lbs", "lb", "imperial", "units", "metric"),
        "Yes: Settings > Units switches to imperial. Data is stored in kg and converted for "
        "display.",
        "settings",
    ),
    Entry(
        "shortcuts",
        "Are there keyboard shortcuts?",
        ("keyboard", "shortcut", "shortcuts", "ctrl", "command bar", "hotkey"),
        "Ctrl+K opens the command bar from anywhere; Ctrl+1 to 0 jump between pages; Enter logs "
        "a set.",
        None,
    ),
    Entry(
        "start_fresh",
        "How do I start fresh?",
        ("start fresh", "erase", "reset", "delete my data", "wipe", "start over"),
        'Settings > Erase my data, or tell me "start fresh". It backs up first, then deletes '
        "your logs and keeps the exercise library and food table.",
        "settings",
    ),
    Entry(
        "cardio",
        "Can I log cardio and yoga?",
        ("cardio", "run", "running", "cycling", "yoga", "meditation", "walk"),
        "Yes. Train has sections for cardio, flexibility and meditation with time-based logging; "
        "they count toward streaks and quests.",
        "workout",
    ),
)

ENTRY_BY_ID: dict[str, Entry] = {e.id: e for e in ENTRIES}

_WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower()):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _key_hits(key: str, text_words: list[str], joined: str) -> float:
    kw = words(key)
    if not kw:
        return 0.0
    if len(kw) > 1:
        return 2.0 if " ".join(kw) in joined else 0.0
    return 1.0 if kw[0] in text_words else 0.0


def score(entry: Entry, text: str) -> float:
    tw = words(text)
    joined = " ".join(tw)
    s = sum(_key_hits(k, tw, joined) for k in entry.keys)
    s += 0.5 * sum(1 for w in words(entry.question) if len(w) > 3 and w in tw)
    return s


def match(text: str, threshold: float = 1.0) -> Entry | None:
    """The best entry for a question, or None when nothing fits well enough."""
    best: tuple[float, Entry] | None = None
    for e in ENTRIES:
        s = score(e, text)
        if s > 0 and (best is None or s > best[0]):
            best = (s, e)
    return best[1] if best and best[0] >= threshold else None


def section_in(text: str) -> str | None:
    """The app section a sentence names, if any (longest name wins)."""
    joined = " ".join(words(text))
    hits = [
        (len(name), sid)
        for sid, names in SECTIONS.items()
        for name in names
        if re.search(rf"\b{re.escape(' '.join(words(name)))}\b", joined)
    ]
    return max(hits)[1] if hits else None
