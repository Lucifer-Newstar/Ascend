# ruff: noqa: E501  (keyword and muscle rule tables read best one rule per line)
"""Add your own exercise: analyse a typed name, propose every field with its source,
and create the exercise once the user has reviewed it.

Pipeline (each later stage may override earlier ones; every field records which
stage set it, and the user's own edits win over all of them):

  1. library   fuzzy match against the library. Close matches are offered as "did you
               mean"; a near-identical one also seeds the proposal (muscles, pattern...).
  2. rules     keyword rules (equipment, section, measure, pattern, muscles, range).
  3. local_ai  the local model (qwen3:4b through Ollama, localhost only), asked for
               structured JSON that is validated field by field; anything invalid is
               dropped and the earlier value stays. Skipped when AI is off or the model
               is not installed: the rules proposal stands on its own.
  4. online    optional online research (wger.de for fields, Wikipedia for a summary),
               only when Settings -> "Online research" is on or the user allowed this one
               lookup. Off by default; with neither, no network request is made at all.

Every proposed field also gets a confidence (high / medium / low) from the stage that set
it; when a core field is low the review says so and offers online research.

See docs/architecture/adr/0013-custom-exercises.md.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.core.events import EventBus, ExerciseAdded
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from app.modules.workouts import library as lib
from app.modules.workouts.models import Exercise, ExerciseMuscle

FIELDS = (
    "section", "equipment", "measure", "pattern", "difficulty", "muscles",
    "rep_low", "rep_high", "met", "instructions", "aliases",
)  # fmt: skip
SECTIONS = ("gym", "calisthenics", "cardio", "martial_arts", "flexibility", "meditation")
EQUIPMENT = (
    "bodyweight", "barbell", "dumbbell", "kettlebell", "cable", "machine", "band", "rings",
    "bar", "bench", "medicine_ball", "exercise_ball", "other",
)  # fmt: skip
PROMPT_ID = "exercise_classify.v1"
PROMPT_FILE = Path(__file__).with_name("prompts") / f"{PROMPT_ID}.txt"
WGER_API = "https://wger.de/api/v2"


class Duplicate(Exception):
    def __init__(self, exercise: Exercise):
        super().__init__(f"'{exercise.name}' is already in the library")
        self.exercise = exercise


@dataclass
class Proposal:
    values: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    attribution: list[dict[str, str]] = field(default_factory=list)
    # Fields the rules filled with a fallback default because no keyword matched.
    guessed: set[str] = field(default_factory=set)

    def put(self, key: str, value: Any, source: str, *, guessed: bool = False) -> None:
        if value is None or value == [] or value == {}:
            return
        self.values[key] = value
        self.sources[key] = source
        if guessed:
            self.guessed.add(key)
        else:
            self.guessed.discard(key)

    def snapshot(self) -> Proposal:
        return Proposal(
            values=json.loads(json.dumps(self.values)),
            sources=dict(self.sources),
            attribution=list(self.attribution),
            guessed=set(self.guessed),
        )


# --- 1. library ----------------------------------------------------------------------------


def _candidates(db: Session) -> list[Exercise]:
    return list(db.scalars(select(Exercise).where(Exercise.archived.is_(False))).all())


def find_duplicate(db: Session, name: str) -> Exercise | None:
    key = lib.normalize(name)
    for e in _candidates(db):
        if lib.normalize(e.name) == key or any(lib.normalize(a) == key for a in e.aliases):
            return e
    return None


def library_matches(db: Session, name: str, limit: int = 5) -> list[tuple[Exercise, float, str]]:
    exercises = {e.id: e for e in _candidates(db)}
    found = lib.best_matches(
        name, [(e.id, e.name, e.aliases) for e in exercises.values()], limit, cutoff=0.7
    )
    return [(exercises[m.exercise_id], m.score, m.via) for m in found]


def _from_library(p: Proposal, e: Exercise) -> None:
    p.put("section", e.section, "library")
    p.put("equipment", e.equipment, "library")
    p.put("measure", e.measure, "library")
    p.put("pattern", e.pattern, "library")
    p.put("difficulty", e.difficulty, "library")
    p.put("muscles", {m.muscle: m.weight for m in e.muscles}, "library")
    p.put("rep_low", e.rep_low, "library")
    p.put("rep_high", e.rep_high, "library")
    p.put("met", e.met, "library")


# --- 2. rules --------------------------------------------------------------------------------

_EQUIPMENT_RULES: tuple[tuple[str, str], ...] = (
    (r"\bbarbell\b|\bbb\b|\bez.?bar\b|\btrap.?bar\b|\blandmine\b", "barbell"),
    (r"\bdumbbells?\b|\bdb\b", "dumbbell"),
    (r"\bkettlebells?\b|\bkb\b", "kettlebell"),
    (r"\bcable\b|\bpulley\b", "cable"),
    (r"\bmachine\b|\bsmith\b|leg press|pec deck|\bhack\b|\bsled\b", "machine"),
    (r"\bband(ed|s)?\b", "band"),
    (r"\brings?\b", "rings"),
    (r"medicine ball|med ball|\bslam\b", "medicine_ball"),
    (r"swiss ball|stability ball|exercise ball", "exercise_ball"),
)
_BODYWEIGHT = re.compile(
    r"push.?up|pull.?up|chin.?up|\bdips?\b|plank|burpee|sit.?up|crunch|lunge|"
    r"pistol|muscle.?up|handstand|lever|l.?sit|hollow|bridge|mountain climber|jumping jack"
)
_SECTION_RULES: tuple[tuple[str, str], ...] = (
    (r"\brun|jog|sprint|cycl|\bbike\b|rowing|\berg\b|swim|skipping|jump rope|elliptical|"
     r"\bhike|\bwalk|stair", "cardio"),
    (r"stretch|mobility|\byoga\b|foam roll", "flexibility"),
    (r"boxing|kickbox|muay|\bbjj\b|jiu.?jitsu|karate|shadow box|sparring|wrestl|silambam", "martial_arts"),
    (r"meditat|breath|mindful", "meditation"),
)  # fmt: skip
_HOLD = re.compile(
    r"\bhold\b|plank|\bhang\b|lever|l.?sit|v.?sit|hollow|wall sit|isometric|planche|flag\b"
)
_MUSCLE_RULES: tuple[tuple[str, dict[str, float]], ...] = (
    (r"incline.*(press|fly|push)", {"upper_chest": 1, "lower_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}),
    (r"bench|chest press|push.?up|\bfly|flye|pec deck|floor press", {"lower_chest": 1, "upper_chest": 0.5, "front_delts": 0.5, "triceps": 0.5}),
    (r"overhead|shoulder press|military|pike push|handstand push|arnold|push press", {"front_delts": 1, "side_delts": 0.5, "triceps": 0.5}),
    (r"lateral raise|side raise|upright row", {"side_delts": 1, "traps": 0.5}),
    (r"rear delt|face pull|reverse fl", {"rear_delts": 1, "rhomboids": 0.5}),
    (r"pull.?up|chin.?up|pulldown|pull.?down|\blat\b|muscle.?up|lever", {"lats": 1, "biceps": 0.5, "rhomboids": 0.5}),
    (r"\brow\b|\brows\b", {"lats": 1, "rhomboids": 1, "rear_delts": 0.5, "biceps": 0.5}),
    (r"(?<!leg )(?<!hamstring )curl", {"biceps": 1, "forearms": 0.5}),
    (r"tricep|pushdown|skull|kickback|close.?grip", {"triceps": 1}),
    (r"\bdips?\b", {"triceps": 1, "lower_chest": 0.5, "front_delts": 0.5}),
    (r"squat|leg press|wall sit", {"quads": 1, "glutes": 1, "adductors": 0.5}),
    (r"lunge|split squat|step.?up", {"quads": 1, "glutes": 1, "adductors": 0.5}),
    (r"deadlift|\brdl\b|good morning|jefferson", {"hamstrings": 1, "glutes": 1, "lower_back": 1, "forearms": 0.5}),
    (r"hip thrust|glute bridge|\bbridge\b|kickback.*glute", {"glutes": 1, "hamstrings": 0.5}),
    (r"leg curl|hamstring curl|nordic|glute.?ham", {"hamstrings": 1}),
    (r"leg extension", {"quads": 1}),
    (r"calf|calves", {"calves": 1}),
    (r"shrug", {"traps": 1}),
    (r"adduct|copenhagen", {"adductors": 1}),
    (r"twist|side plank|woodchop|oblique|pallof|flag\b", {"obliques": 1, "abs": 0.5}),
    (r"crunch|sit.?up|plank|hollow|leg raise|\babs?\b|ab wheel|rollout|v.?up|dragon flag|l.?sit", {"abs": 1, "obliques": 0.5}),
    (r"back extension|hyperextension|superman", {"lower_back": 1, "glutes": 0.5}),
    (r"wrist|grip|farmer", {"forearms": 1, "traps": 0.5}),
    (r"\brun|jog|sprint|stair|\bhike|\bwalk", {"quads": 0.5, "hamstrings": 0.5, "glutes": 0.5, "calves": 0.5}),
    (r"cycl|\bbike\b", {"quads": 0.5, "glutes": 0.5, "calves": 0.5}),
)  # fmt: skip
_BEGINNER = re.compile(r"assisted|\bknee|incline push|wall push|\bbox\b|machine|band.?assisted")
_EXPERT = re.compile(
    r"one.?arm|one.?leg|single.?arm|planche|lever|muscle.?up|human flag|dragon flag|deficit|pistol"
)


def rules_proposal(name: str, equipment_hint: str | None = None) -> Proposal:
    p = Proposal()
    lower = name.lower()
    equipment = equipment_hint if equipment_hint in EQUIPMENT else None
    if equipment is None:
        equipment = next((eq for rx, eq in _EQUIPMENT_RULES if re.search(rx, lower)), None)
    if equipment is None and _BODYWEIGHT.search(lower):
        equipment = "bodyweight"
    section = next((s for rx, s in _SECTION_RULES if re.search(rx, lower)), None)
    section_guessed = section is None and equipment is None
    if section is None:
        section = (
            "calisthenics"
            if equipment in ("bodyweight", "rings", "bar", None) and _BODYWEIGHT.search(lower)
            else "gym"
        )
    measure = lib.map_measure(section, None, name)
    if measure == "reps" and _HOLD.search(lower):
        measure = "hold"
    muscles: dict[str, float] = {}
    if section not in ("meditation",):
        for rx, regions in _MUSCLE_RULES:
            if re.search(rx, lower):
                for region, w in regions.items():
                    muscles[region] = max(muscles.get(region, 0.0), float(w))
                if section == "gym" or section == "calisthenics":
                    break  # the first (most specific) strength rule decides
    pattern = lib.map_pattern(name, None, "static" if measure == "hold" else None, [])
    pattern_guessed = pattern == "other"
    if section == "cardio":
        pattern = "locomotion"
    elif section == "flexibility":
        pattern = "mobility"
    if section in ("cardio", "flexibility"):
        pattern_guessed = False
    difficulty = (
        "beginner"
        if _BEGINNER.search(lower)
        else "expert"
        if _EXPERT.search(lower)
        else "intermediate"
    )
    difficulty_guessed = not (_BEGINNER.search(lower) or _EXPERT.search(lower))
    low, high = lib.default_range(measure)
    p.put("section", section, "rules", guessed=section_guessed)
    no_gear = section in ("cardio", "meditation")
    p.put(
        "equipment",
        equipment or ("none" if no_gear else "other"),
        "rules",
        guessed=equipment is None and not no_gear,
    )
    p.put("measure", measure, "rules")
    p.put("pattern", pattern, "rules", guessed=pattern_guessed)
    p.put(
        "difficulty",
        difficulty if section in ("gym", "calisthenics") else None,
        "rules",
        guessed=difficulty_guessed,
    )
    p.put("muscles", muscles, "rules")
    p.put("rep_low", low, "rules")
    p.put("rep_high", high, "rules")
    return p


# --- 3. local model ----------------------------------------------------------------------------

AI_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["section", "equipment", "measure", "pattern", "difficulty", "muscles"],
    "properties": {
        "section": {"enum": list(SECTIONS)},
        "equipment": {"enum": list(EQUIPMENT)},
        "measure": {"enum": list(lib.MEASURES)},
        "pattern": {"enum": list(lib.PATTERNS)},
        "difficulty": {"enum": list(lib.DIFFICULTIES)},
        "muscles": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["region", "role"],
                "properties": {
                    "region": {"enum": list(MUSCLE_BY_KEY)},
                    "role": {"enum": ["primary", "secondary"]},
                },
            },
        },
        "instructions": {
            "type": "array",
            "maxItems": 5,
            "items": {"type": "string", "maxLength": 200},
        },
        "aliases": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 60}},
    },
}


class _AiMuscle(BaseModel):
    region: str
    role: str

    @field_validator("region")
    @classmethod
    def _region(cls, v: str) -> str:
        if v not in MUSCLE_BY_KEY:
            raise ValueError("unknown region")
        return v


class _AiReply(BaseModel):
    """Every field optional here: each one is checked on its own and dropped if bad."""

    section: str | None = None
    equipment: str | None = None
    measure: str | None = None
    pattern: str | None = None
    difficulty: str | None = None
    muscles: list[dict[str, Any]] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


@dataclass
class AiResult:
    status: str  # ok | off | unavailable | error | invalid
    detail: str = ""
    model: str | None = None
    applied: list[str] = field(default_factory=list)


def ask_model(
    host: str, model: str, name: str, notes: str, timeout: float = 25.0
) -> dict[str, Any]:
    """One structured call to the local model. Raises on transport or JSON errors."""
    prompt = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .replace("{{name}}", name)
        .replace("{{notes}}", notes or "none")
    )
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "format": AI_SCHEMA,
        "options": {"temperature": 0, "num_predict": 400},
        "messages": [{"role": "user", "content": prompt}],
    }
    r = httpx.post(f"{host}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    content = r.json().get("message", {}).get("content", "")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    return data


def apply_ai(p: Proposal, raw: dict[str, Any]) -> list[str]:
    """Validate the model's reply field by field; apply what passes. Returns applied keys."""
    try:
        reply = _AiReply.model_validate(raw)
    except ValidationError:
        return []
    applied: list[str] = []
    checks = {
        "section": SECTIONS,
        "equipment": EQUIPMENT,
        "measure": lib.MEASURES,
        "pattern": lib.PATTERNS,
        "difficulty": lib.DIFFICULTIES,
    }
    for key, allowed in checks.items():
        value = getattr(reply, key)
        if value in allowed:
            p.put(key, value, "local_ai")
            applied.append(key)
    muscles: dict[str, float] = {}
    for item in reply.muscles[:6]:
        try:
            m = _AiMuscle.model_validate(item)
        except ValidationError:
            continue
        w = 1.0 if m.role == "primary" else 0.5
        muscles[m.region] = max(muscles.get(m.region, 0.0), w)
    if muscles and any(w == 1.0 for w in muscles.values()):
        p.put("muscles", muscles, "local_ai")
        applied.append("muscles")
    steps = [
        s.strip() for s in reply.instructions if isinstance(s, str) and 3 <= len(s.strip()) <= 200
    ][:5]
    if steps:
        p.put("instructions", steps, "local_ai")
        applied.append("instructions")
    aliases = [
        a.strip() for a in reply.aliases if isinstance(a, str) and 2 <= len(a.strip()) <= 60
    ][:4]
    if aliases:
        p.put("aliases", aliases, "local_ai")
        applied.append("aliases")
    if "measure" in applied:
        low, high = lib.default_range(p.values["measure"])
        if p.sources.get("rep_low") != "library":
            p.put("rep_low", low, "rules")
            p.put("rep_high", high, "rules")
    return applied


# --- 4. online research (optional) -------------------------------------------------------------
#
# Only ever reached through `research()`, which `analyse()` calls only when Settings ->
# "Online research" is on or the user allowed this single lookup. The exercise name is the
# only thing sent. Sources (licences checked, see ADR-0013):
#   * wger.de exercise API: exercise data under CC-BY-SA 4.0 (licence and author per
#     exercise come back in the API and are stored as attribution). Fills fields.
#   * Wikipedia REST page summary: text under CC BY-SA 4.0. Used for a one-paragraph
#     summary in the report only, never for structured fields, and only when the article
#     title matches the name (a redirect to a generic article such as "Exercise" is ignored).
#   * Wikidata (CC0) was checked and is not queried: exercise items carry no muscle or
#     equipment statements, so it would add a request without adding a field.

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
USER_AGENT = f"ASCEND-desktop/{__version__} (offline fitness app; user-initiated exercise lookups)"
RESEARCH_TIMEOUT = httpx.Timeout(6.0, connect=4.0)

WGER_MUSCLES: dict[str, dict[str, float]] = {
    "Biceps": {"biceps": 1},
    "Brachialis": {"biceps": 1},
    "Shoulders": {"front_delts": 1, "side_delts": 0.5},
    "Serratus anterior": {"abs": 0.5},
    "Chest": {"lower_chest": 1, "upper_chest": 0.5},
    "Triceps": {"triceps": 1},
    "Abs": {"abs": 1},
    "Obliques": {"obliques": 1},
    "Calves": {"calves": 1},
    "Soleus": {"calves": 1},
    "Glutes": {"glutes": 1},
    "Traps": {"traps": 1},
    "Quads": {"quads": 1},
    "Hamstrings": {"hamstrings": 1},
    "Lats": {"lats": 1},
    # wger leaves name_en empty for some muscles; their Latin names map the same way.
    "Biceps brachii": {"biceps": 1},
    "Anterior deltoid": {"front_delts": 1},
    "Pectoralis major": {"lower_chest": 1, "upper_chest": 0.5},
    "Triceps brachii": {"triceps": 1},
    "Rectus abdominis": {"abs": 1},
    "Obliquus externus abdominis": {"obliques": 1},
    "Gastrocnemius": {"calves": 1},
    "Gluteus maximus": {"glutes": 1},
    "Trapezius": {"traps": 1},
    "Quadriceps femoris": {"quads": 1},
    "Biceps femoris": {"hamstrings": 1},
    "Latissimus dorsi": {"lats": 1},
}
WGER_EQUIPMENT: dict[str, str] = {
    "Barbell": "barbell",
    "SZ-Bar": "barbell",
    "Dumbbell": "dumbbell",
    "Kettlebell": "kettlebell",
    "Pull-up bar": "bar",
    "none (bodyweight exercise)": "bodyweight",
    "Bench": "bench",
    "Incline bench": "bench",
    "Swiss Ball": "exercise_ball",
    "Resistance band": "band",
    "Gym mat": "bodyweight",
}


FIELD_LABELS = {
    "section": "Type",
    "equipment": "Equipment",
    "measure": "Measured in",
    "pattern": "Movement pattern",
    "difficulty": "Difficulty",
    "muscles": "Muscles",
    "instructions": "Instructions",
}


@dataclass
class OnlineResult:
    status: str  # off | not_requested | ok | not_found | offline | timeout | rate_limited | error
    detail: str = ""
    applied: list[str] = field(default_factory=list)


@dataclass
class SourceCall:
    source: str  # wger | wikipedia
    url: str
    status: str  # ok | not_found | offline | timeout | rate_limited | error | skipped


@dataclass
class Research:
    """What online research found, ready for the report the user confirms."""

    query: str
    consent: str  # setting | once
    calls: list[SourceCall] = field(default_factory=list)
    wger: dict[str, Any] | None = None
    summary: str = ""
    summary_url: str = ""

    @property
    def outcome(self) -> str:
        statuses = [c.status for c in self.calls]
        if self.wger is not None or self.summary:
            return "ok"
        for bad in ("rate_limited", "timeout", "offline", "error"):
            if bad in statuses:
                return bad
        return "not_found"


def _strip_html(text: str) -> list[str]:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    plain = re.sub(r"\s+", " ", plain).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if len(s.strip()) > 3]
    return [s[:300] for s in sentences[:8]]


def _hyphenate(text: str) -> str:
    return re.sub(r"(?i)\b(push|pull|chin|sit|step) ?up", lambda m: m.group(1) + "-up", text)


def name_variants(name: str) -> list[str]:
    """wger filters translations by exact, case-sensitive name and has no search endpoint
    (it answers 404), so try the spellings people and wger actually use: as typed, Title
    Case, Sentence case, lower case, each also with "push-up"-style hyphens. At most 6."""
    base = re.sub(r"\s+", " ", name).strip()
    out: list[str] = []
    for form in (base, base.title(), base.capitalize(), base.lower()):
        out += [form, _hyphenate(form)]
    return list(dict.fromkeys(v for v in out if v))[:6]


def _status_of(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return "rate_limited"
    if isinstance(exc, httpx.TransportError):
        return "offline"
    return "error"


def wger_lookup(name: str, client: httpx.Client, calls: list[SourceCall]) -> dict[str, Any] | None:
    key = lib.normalize(name)
    for variant in name_variants(name):
        url = f"{WGER_API}/exercise-translation/"
        r = client.get(url, params={"name": variant, "language": 2})
        r.raise_for_status()
        # Unknown filters are ignored by the API (it would return every exercise), so a
        # result only counts when its name really is the name asked for.
        results = [
            x for x in r.json().get("results", []) if lib.normalize(str(x.get("name", ""))) == key
        ]
        if not results:
            calls.append(SourceCall("wger", str(r.request.url), "not_found"))
            continue
        tr = results[0]
        calls.append(SourceCall("wger", str(r.request.url), "ok"))
        info = client.get(f"{WGER_API}/exerciseinfo/{int(tr['exercise'])}/")
        info.raise_for_status()
        calls.append(SourceCall("wger", str(info.request.url), "ok"))
        return {"translation": tr, "info": info.json()}
    return None


def wikipedia_summary(
    name: str, client: httpx.Client, calls: list[SourceCall]
) -> tuple[str, str] | None:
    title = re.sub(r"\s+", "_", name.strip().capitalize())
    url = f"{WIKIPEDIA_API}/{title}"
    r = client.get(url, params={"redirect": "true"})
    if r.status_code == 404:
        calls.append(SourceCall("wikipedia", url, "not_found"))
        return None
    r.raise_for_status()
    data = r.json()
    found = str(data.get("title") or "")
    # Only an article about this exercise; a redirect to a broad topic is not evidence.
    if data.get("type") != "standard" or lib.normalize(found) != lib.normalize(name):
        calls.append(SourceCall("wikipedia", url, "not_found"))
        return None
    calls.append(SourceCall("wikipedia", url, "ok"))
    extract = re.sub(r"\s+", " ", str(data.get("extract") or "")).strip()
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    summary = " ".join(sentences[:2])[:400]
    page = str(((data.get("content_urls") or {}).get("desktop") or {}).get("page") or "")
    return summary, page or f"https://en.wikipedia.org/wiki/{title}"


def research(name: str, client: httpx.Client, consent: str) -> Research:
    """Ask wger, then Wikipedia. Every failure is caught and recorded; never raises."""
    res = Research(query=name, consent=consent)
    try:
        res.wger = wger_lookup(name, client, res.calls)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
        res.calls.append(SourceCall("wger", f"{WGER_API}/exercise-translation/", _status_of(e)))
    # Skip Wikipedia when wger already showed the network is down or rate limited.
    if any(c.status in ("offline", "timeout") for c in res.calls):
        res.calls.append(SourceCall("wikipedia", WIKIPEDIA_API, "skipped"))
        return res
    try:
        found = wikipedia_summary(name, client, res.calls)
        if found:
            res.summary, res.summary_url = found
    except (httpx.HTTPError, ValueError, TypeError) as e:
        res.calls.append(SourceCall("wikipedia", WIKIPEDIA_API, _status_of(e)))
    return res


def apply_wger(p: Proposal, found: dict[str, Any]) -> list[str]:
    tr, info = found["translation"], found["info"]
    applied: list[str] = []
    muscles: dict[str, float] = {}
    for key, scale in (("muscles", 1.0), ("muscles_secondary", 0.5)):
        for m in info.get(key, []) or []:
            label = str(m.get("name_en") or m.get("name") or "")
            regions = WGER_MUSCLES.get(label) or WGER_MUSCLES.get(str(m.get("name") or ""), {})
            for region, w in regions.items():
                muscles[region] = max(muscles.get(region, 0.0), w * scale)
    if muscles and any(w == 1.0 for w in muscles.values()):
        p.put("muscles", muscles, "wger")
        applied.append("muscles")
    equipment = [
        WGER_EQUIPMENT.get(str(e.get("name")), "") for e in info.get("equipment", []) or []
    ]
    equipment = [e for e in equipment if e and e not in ("bench",)] or [e for e in equipment if e]
    if equipment:
        p.put("equipment", equipment[0], "wger")
        applied.append("equipment")
    if str((info.get("category") or {}).get("name")) == "Cardio":
        p.put("section", "cardio", "wger")
        applied.append("section")
    elif equipment and "section" in p.guessed:
        section = "calisthenics" if equipment[0] in ("bodyweight", "bar", "rings") else "gym"
        p.put("section", section, "wger")
        applied.append("section")
    steps = _strip_html(str(tr.get("description") or ""))
    if steps:
        p.put("instructions", steps, "wger")
        applied.append("instructions")
    lic = info.get("license") or {}
    author = str(info.get("license_author") or "").strip()
    p.attribution.append(
        {
            "source": "wger",
            "title": f"wger exercise #{int(tr['exercise'])}: {tr.get('name')}"
            + (f" (by {author[:60]})" if author else ""),
            "url": f"https://wger.de/en/exercise/{int(tr['exercise'])}/view/",
            "license": str(lic.get("short_name") or "see wger.de"),
        }
    )
    return applied


# --- confidence --------------------------------------------------------------------------------

CORE_FIELDS = ("section", "equipment", "measure", "pattern", "muscles")


def confidence(p: Proposal, seed_score: float | None) -> dict[str, str]:
    """high: the user, an exact wger match, or a near-identical library exercise.
    medium: a looser library match, a validated local-model answer, a keyword rule.
    low: a rules fallback (no keyword matched) or nothing at all."""
    out: dict[str, str] = {}
    for key in (*CORE_FIELDS, "difficulty", "instructions"):
        src = p.sources.get(key)
        if src is None:
            out[key] = "low"
        elif src in ("user", "wger"):
            out[key] = "high"
        elif src == "library":
            out[key] = "high" if (seed_score or 0) >= 0.95 else "medium"
        elif src == "local_ai":
            out[key] = "medium"
        else:
            out[key] = "low" if key in p.guessed else "medium"
    return out


def insufficient(p: Proposal, conf: dict[str, str]) -> list[str]:
    """Core fields the offline stages could not support. Muscles are not needed for
    meditation or mobility, so their absence there is not a gap."""
    gaps = [k for k in CORE_FIELDS if conf.get(k) == "low"]
    if p.values.get("section") in ("meditation", "flexibility") and "muscles" in gaps:
        gaps.remove("muscles")
    return gaps


def _display(key: str, value: Any) -> str:
    if value is None:
        return "-"
    if key == "muscles" and isinstance(value, dict):
        primary = [k for k, w in value.items() if w >= 1.0]
        secondary = [k for k, w in value.items() if w < 1.0]
        text = ", ".join(primary)
        return text + (f" (+ {', '.join(secondary)})" if secondary else "")
    if key == "instructions" and isinstance(value, list):
        return f"{len(value)} steps"
    return str(value)


def report_fields(offline: Proposal, final: Proposal, res: Research) -> list[dict[str, Any]]:
    """One row per field online research set: its value, the link it came from, and the
    offline guess it replaces (so a conflict is visible and the user can keep either)."""
    rows: list[dict[str, Any]] = []
    url = ""
    if res.wger is not None:
        url = f"https://wger.de/en/exercise/{int(res.wger['translation']['exercise'])}/view/"
    for key in FIELD_LABELS:
        if final.sources.get(key) != "wger":
            continue
        new, old = final.values.get(key), offline.values.get(key)
        rows.append(
            {
                "field": key,
                "label": FIELD_LABELS[key],
                "value": _display(key, new),
                "source": "wger",
                "url": url,
                "offline_value": _display(key, old),
                "offline_source": offline.sources.get(key, ""),
                "conflict": old is not None and old != new,
            }
        )
    return rows


# --- analyse / create ---------------------------------------------------------------


@dataclass
class Analysis:
    name: str
    proposal: Proposal
    matches: list[tuple[Exercise, float, str]]
    duplicate: Exercise | None
    ai: AiResult
    online: OnlineResult
    confidence: dict[str, str] = field(default_factory=dict)
    insufficient: list[str] = field(default_factory=list)
    offline: Proposal | None = None
    research: Research | None = None
    report: list[dict[str, Any]] = field(default_factory=list)


def analyse(
    db: Session,
    name: str,
    *,
    equipment_hint: str | None,
    notes: str,
    ai_enabled: bool,
    ollama_host: str,
    model: str,
    online_allowed: bool,
    online_requested: bool,
    allow_once: bool = False,
    now: datetime | None = None,
    http: httpx.Client | None = None,
) -> Analysis:
    """online_allowed: the Settings toggle. allow_once: the user allowed this lookup only.
    Online research runs when it is permitted (either of those) AND wanted (the user asked,
    or the setting is on and the offline proposal is insufficient). Otherwise no client is
    even created."""
    name = re.sub(r"\s+", " ", name).strip()
    matches = library_matches(db, name)
    duplicate = find_duplicate(db, name)
    p = rules_proposal(name, equipment_hint)
    seed_hit = next(((e, score) for e, score, _ in matches if score >= 0.85), None)
    if seed_hit is not None:
        _from_library(p, seed_hit[0])
    seed_score = seed_hit[1] if seed_hit else None
    # Local model.
    from app.modules.coach import ollama

    if not ai_enabled:
        ai = AiResult("off", "AI is turned off in Settings")
    elif not ollama.is_available(ollama_host, model):
        ai = AiResult("unavailable", f"{model} is not installed or Ollama is not running", model)
    else:
        try:
            raw = ask_model(ollama_host, model, name, notes)
            applied = apply_ai(p, raw)
            ai = AiResult(
                "ok" if applied else "invalid", "" if applied else "no valid fields", model, applied
            )
        except (httpx.HTTPError, ValueError) as e:
            ai = AiResult("error", str(e)[:120], model)
    _make_consistent(p)
    offline_conf = confidence(p, seed_score)
    gaps = insufficient(p, offline_conf)
    # Online research.
    permitted = online_allowed or allow_once
    wanted = online_requested or (online_allowed and bool(gaps))
    res: Research | None = None
    offline: Proposal | None = None
    if not wanted:
        online = OnlineResult("not_requested" if permitted else "off")
    elif not permitted:
        online = OnlineResult(
            "off", "Online research is off: allow this lookup once or turn it on in Settings"
        )
    else:
        offline = p.snapshot()
        consent = "setting" if online_allowed else "once"
        client = http or httpx.Client(
            timeout=RESEARCH_TIMEOUT,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        try:
            res = research(name, client, consent)
        finally:
            if http is None:
                client.close()
        applied = apply_wger(p, res.wger) if res.wger is not None else []
        if res.summary:
            p.attribution.append(
                {
                    "source": "wikipedia",
                    "title": f"Wikipedia: {name}",
                    "url": res.summary_url,
                    "license": "CC BY-SA 4.0",
                }
            )
        details = {
            "ok": "",
            "not_found": "No exercise with this name on wger.de or Wikipedia",
            "offline": "No internet connection; the offline proposal stands",
            "timeout": "The lookup timed out; the offline proposal stands",
            "rate_limited": "wger.de asked us to slow down; try again in a minute",
            "error": "The lookup failed; the offline proposal stands",
        }
        online = OnlineResult(res.outcome, details[res.outcome], applied)
        _make_consistent(p)
        _log(db, res, now or datetime.now())
    conf = confidence(p, seed_score)
    report = report_fields(offline, p, res) if (offline is not None and res is not None) else []
    return Analysis(
        name,
        p,
        matches,
        duplicate,
        ai,
        online,
        confidence=conf,
        insufficient=insufficient(p, conf),
        offline=offline,
        research=res,
        report=report,
    )


def _log(db: Session, res: Research, now: datetime) -> None:
    from app.modules.workouts.models import OnlineLookupLog

    db.add(
        OnlineLookupLog(
            at=now,
            query=res.query[:80],
            sources_json=json.dumps(
                [{"source": c.source, "url": c.url[:300], "status": c.status} for c in res.calls]
            ),
            outcome=res.outcome,
            consent=res.consent,
            detail="",
        )
    )
    db.flush()


TIMED_SECTIONS = ("cardio", "martial_arts", "flexibility", "meditation")


def _make_consistent(p: Proposal) -> None:
    """The stages can disagree (a model saying 'cardio' and 'reps'); fix the proposal so
    it passes the same checks as create: measure follows section, at most 3 primaries."""
    v = p.values
    timed = v.get("section") in TIMED_SECTIONS
    if timed and v.get("measure") != "time":
        p.put("measure", "time", "rules")
    elif not timed and v.get("measure") == "time":
        p.put("measure", "reps", "rules")
    if v["measure"] == "time":
        for key in ("rep_low", "rep_high"):
            v.pop(key, None)
            p.sources.pop(key, None)
    elif v.get("rep_low") is None:
        low, high = lib.default_range(v["measure"])
        p.put("rep_low", low, "rules")
        p.put("rep_high", high, "rules")
    muscles = dict(v.get("muscles") or {})
    primaries = [k for k, w in muscles.items() if w >= 1.0]
    if len(primaries) > 3:
        for k in primaries[3:]:
            muscles[k] = 0.5
        v["muscles"] = muscles


def unique_slug(db: Session, name: str) -> str:
    base = lib.slugify(name) or "exercise"
    slug, n = f"custom-{base}", 2
    while db.scalar(select(Exercise.id).where(Exercise.slug == slug)) is not None:
        slug, n = f"custom-{base}-{n}", n + 1
    return slug


def create(
    db: Session,
    bus: EventBus,
    now: datetime,
    *,
    name: str,
    values: dict[str, Any],
    field_sources: dict[str, str],
    attribution: list[dict[str, str]],
) -> Exercise:
    name = re.sub(r"\s+", " ", name).strip()
    dup = find_duplicate(db, name)
    if dup is not None:
        raise Duplicate(dup)
    for alias in values.get("aliases") or []:
        clash = find_duplicate(db, alias)
        if clash is not None:
            raise Duplicate(clash)
    measure = values["measure"]
    e = Exercise(
        name=name,
        equipment=values["equipment"],
        section=values["section"],
        met=values.get("met"),
        slug=unique_slug(db, name),
        measure=measure,
        difficulty=values.get("difficulty"),
        pattern=values["pattern"],
        mechanic=None,
        instructions_json=json.dumps(values.get("instructions") or []),
        aliases_json=json.dumps(values.get("aliases") or []),
        image=None,
        source="custom",
        source_ref=None,
        field_sources_json=json.dumps(field_sources),
        rep_low=values.get("rep_low"),
        rep_high=values.get("rep_high"),
        is_custom=True,
        archived=False,
        attribution_json=json.dumps(attribution),
        created_at=now,
    )
    e.muscles = [ExerciseMuscle(muscle=k, weight=w) for k, w in values["muscles"].items()]
    db.add(e)
    db.flush()
    bus.publish(
        db,
        ExerciseAdded(
            exercise_id=e.id,
            name=e.name,
            source="custom",
            field_sources=json.dumps(field_sources, sort_keys=True),
            at=now,
        ),
    )
    return e
