from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from app.modules.skills import service as skills
from app.modules.workouts import custom, deload_service, service
from app.modules.workouts.activity_seed import SECTIONS
from app.modules.workouts.models import Exercise, OnlineLookupLog
from app.modules.workouts.schemas import (
    AttributionOut,
    CustomExerciseIn,
    ExerciseAnalysis,
    ExerciseAnalyzeIn,
    ExerciseDetail,
    ExerciseMatch,
    ExerciseOut,
    ExerciseProposal,
    FinishedWorkout,
    LoggedSet,
    OnlineLogEntry,
    PreviousSession,
    PROut,
    ResearchCall,
    ResearchField,
    ResearchReport,
    SetIn,
    SetOut,
    SetPatch,
    StageStatus,
    UnlockedStep,
    WorkoutOut,
    WorkoutSummary,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])
exercises_router = APIRouter(prefix="/exercises", tags=["workouts"])
prs_router = APIRouter(prefix="/prs", tags=["workouts"])
deload_router = APIRouter(prefix="/deload", tags=["workouts"])


@deload_router.get("", response_model=deload_service.DeloadOut)
def deload_advice(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> deload_service.DeloadOut:
    """Is a deload week due? Planned after 3 training weeks, or reactive when 2 of the
    4 fatigue signals hold. Each signal is listed with the numbers behind it."""
    return deload_service.advice(db, now)


@deload_router.post("/start", response_model=deload_service.DeloadOut)
def start_deload(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> deload_service.DeloadOut:
    """Accept the deload: the current week is recorded as the deload week."""
    return deload_service.start_deload_week(db, now)


@prs_router.get("", response_model=list[PROut])
def list_prs(exercise_id: int | None = None, db: Session = Depends(get_db)) -> list[PROut]:
    """Best Epley e1RM per exercise (sets of 1-10 reps with load), highest first."""
    return service.personal_records(db, exercise_id)


@exercises_router.get("", response_model=list[ExerciseOut])
def list_exercises(
    q: str = "",
    section: str | None = None,
    muscle: str | None = None,
    equipment: str | None = None,
    difficulty: Literal["beginner", "intermediate", "expert"] | None = None,
    custom: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ExerciseOut]:
    """The exercise library (gallery and logger). `q` matches names and aliases; the other
    filters narrow by logger section, a muscle region it trains (weight >= 0.5),
    equipment, difficulty, or user-added (`custom=true`). Archived exercises are hidden."""
    if section is not None and section not in SECTIONS:
        raise HTTPException(422, f"unknown section '{section}'")
    if muscle is not None and muscle not in MUSCLE_BY_KEY:
        raise HTTPException(422, f"unknown muscle '{muscle}'")
    f = service.ExerciseFilter(
        q=q,
        section=section,
        muscle=muscle,
        equipment=equipment,
        difficulty=difficulty,
        custom=custom,
    )
    return [service.exercise_out(e) for e in service.list_exercises(db, f=f)]


def _proposal_out(v: dict[str, object]) -> ExerciseProposal:
    muscles = v.get("muscles") or {}
    assert isinstance(muscles, dict)
    return ExerciseProposal.model_validate(
        {
            "section": v["section"],
            "equipment": v["equipment"],
            "measure": v["measure"],
            "pattern": v["pattern"],
            "difficulty": v.get("difficulty"),
            "muscles": [{"muscle": k, "weight": w} for k, w in muscles.items()],
            "rep_low": v.get("rep_low"),
            "rep_high": v.get("rep_high"),
            "met": v.get("met"),
            "instructions": v.get("instructions") or [],
            "aliases": v.get("aliases") or [],
        }
    )


@exercises_router.post("/analyze", response_model=ExerciseAnalysis)
def analyze_exercise(
    body: ExerciseAnalyzeIn,
    request: Request,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> ExerciseAnalysis:
    """Propose every field of a new exercise, each with its source and a confidence:
    library match, rules, the local model (when AI is on and installed) and online
    research (wger.de, Wikipedia) only when Settings -> "Online research" is on or the
    request carries allow_once. `insufficient` lists core fields the offline stages could
    not support. Each online lookup is written to the local lookup log. Nothing else is
    saved."""
    from app.modules.progress import service as progress

    settings = request.app.state.settings
    a = custom.analyse(
        db,
        body.name,
        equipment_hint=body.equipment,
        notes=body.notes,
        ai_enabled=progress.ai_enabled(db),
        ollama_host=settings.ollama_host,
        model=settings.coach_model,
        online_allowed=progress.online_lookup(db),
        online_requested=body.online,
        allow_once=body.allow_once,
        now=now,
        http=getattr(request.app.state, "research_client", None),
    )

    def match(e: Exercise, score: float, via: str) -> ExerciseMatch:
        return ExerciseMatch(
            id=e.id, name=e.name, score=score, via=via, section=e.section, image=e.image
        )

    research = None
    if a.research is not None:
        research = ResearchReport(
            query=a.research.query,
            consent=a.research.consent,
            outcome=a.research.outcome,
            calls=[
                ResearchCall(source=x.source, url=x.url, status=x.status) for x in a.research.calls
            ],
            fields=[ResearchField.model_validate(f) for f in a.report],
            summary=a.research.summary,
            summary_url=a.research.summary_url,
        )
    return ExerciseAnalysis(
        name=a.name,
        proposal=_proposal_out(a.proposal.values),
        field_sources=a.proposal.sources,
        confidence=a.confidence,
        insufficient=a.insufficient,
        offline=_proposal_out(a.offline.values) if a.offline else None,
        offline_sources=a.offline.sources if a.offline else {},
        research=research,
        attribution=[AttributionOut(**x) for x in a.proposal.attribution],
        matches=[match(*m) for m in a.matches],
        duplicate_of=match(a.duplicate, 1.0, "exact") if a.duplicate else None,
        ai=StageStatus(
            status=a.ai.status, detail=a.ai.detail, model=a.ai.model, applied=a.ai.applied
        ),
        online=StageStatus(
            status=a.online.status, detail=a.online.detail, applied=a.online.applied
        ),
    )


@exercises_router.get("/online-log", response_model=list[OnlineLogEntry])
def online_log(
    limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)
) -> list[OnlineLogEntry]:
    """The local log of online research requests, newest first: when, what name was
    looked up, which sources were asked (with each request's outcome) and how it was
    allowed (the setting, or allow once). Never leaves this PC."""
    rows = db.scalars(
        select(OnlineLookupLog)
        .order_by(OnlineLookupLog.at.desc(), OnlineLookupLog.id.desc())
        .limit(limit)
    ).all()
    return [
        OnlineLogEntry(
            id=r.id,
            at=r.at,
            query=r.query,
            sources=[ResearchCall.model_validate(s) for s in r.sources],
            outcome=r.outcome,
            consent=r.consent,
        )
        for r in rows
    ]


@exercises_router.delete("/online-log", status_code=204)
def clear_online_log(db: Session = Depends(get_db)) -> Response:
    """Delete every entry of the online research log."""
    db.execute(delete(OnlineLookupLog))
    db.flush()
    return Response(status_code=204)


@exercises_router.post("", response_model=ExerciseDetail, status_code=201)
def create_exercise(
    body: CustomExerciseIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> ExerciseDetail:
    """Save a reviewed custom exercise and publish ExerciseAdded. 409 when the name or
    an alias already exists (use that exercise instead)."""
    values = body.model_dump(exclude={"name", "field_sources", "attribution"})
    values["muscles"] = {m.muscle: m.weight for m in body.muscles}
    try:
        e = custom.create(
            db,
            bus,
            now,
            name=body.name,
            values=values,
            field_sources=dict(body.field_sources),
            attribution=[x.model_dump() for x in body.attribution],
        )
    except custom.Duplicate as d:
        raise HTTPException(
            409, f"'{d.exercise.name}' is already in the library (id {d.exercise.id})"
        ) from d
    return service.exercise_detail(db, e.id)


@exercises_router.delete("/{exercise_id}", status_code=204)
def archive_exercise(exercise_id: int, db: Session = Depends(get_db)) -> Response:
    """Archive one of your own exercises: hidden from the library and pickers, its
    logged sets and stats stay. Library exercises cannot be removed (409)."""
    e = db.get(Exercise, exercise_id)
    if e is None:
        raise HTTPException(404, f"exercise {exercise_id} not found")
    if not e.is_custom:
        raise HTTPException(409, "only exercises you added can be removed")
    e.archived = True
    db.flush()
    return Response(status_code=204)


@exercises_router.get("/{exercise_id}/previous", response_model=PreviousSession | None)
def previous_session(exercise_id: int, db: Session = Depends(get_db)) -> PreviousSession | None:
    """The last finished session's sets of this exercise (the logger shows them in grey
    as "last time"), or null when it was never logged before."""
    try:
        return service.previous_session(db, exercise_id)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


@exercises_router.get("/{exercise_id}", response_model=ExerciseDetail)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseDetail:
    """One exercise with its instructions, the source of each field, attribution for
    anything found online, the skill trees it belongs to and how often it was logged."""
    try:
        return service.exercise_detail(db, exercise_id)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


@router.post("", response_model=WorkoutOut, status_code=201)
def start(
    section: str = "gym", db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> WorkoutOut:
    """Start a session (or return the one already running). `section` is a hint; the
    first logged set decides it."""
    if section not in SECTIONS:
        raise HTTPException(422, f"unknown section '{section}'")
    existing = service.active_workout(db)
    workout = existing or service.start_workout(db, now, section)
    return service.workout_out(workout)


@router.get("", response_model=list[WorkoutSummary])
def list_workouts(
    limit: int = Query(default=20, ge=1, le=100),
    before: datetime | None = None,
    section: str | None = None,
    source: Literal["app", "strong", "hevy"] | None = None,
    since: date | None = Query(default=None, description="First day to include"),
    until: date | None = Query(default=None, description="Last day to include"),
    db: Session = Depends(get_db),
) -> list[WorkoutSummary]:
    """Newest first. Pass the last item's started_at as `before` for the next page.
    Optional filters: section, source (app or an import) and a day range."""
    if section is not None and section not in SECTIONS:
        raise HTTPException(422, f"unknown section {section!r}")
    if since and until and since > until:
        raise HTTPException(422, "since must be on or before until")
    return service.list_workouts(
        db,
        limit=limit,
        before=before,
        filters=service.WorkoutFilters(section=section, source=source, since=since, until=until),
    )


@router.get("/active", response_model=WorkoutOut | None)
def active(db: Session = Depends(get_db)) -> WorkoutOut | None:
    w = service.active_workout(db)
    return service.workout_out(w) if w else None


@router.get("/{workout_id}", response_model=WorkoutOut)
def get(workout_id: int, db: Session = Depends(get_db)) -> WorkoutOut:
    try:
        return service.workout_out(service.get_workout(db, workout_id))
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e


@router.post("/{workout_id}/sets", response_model=LoggedSet, status_code=201)
def log_set(
    workout_id: int,
    body: SetIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> LoggedSet:
    try:
        row, previous = service.log_set(db, bus, workout_id, body, now)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Invalid as e:
        raise HTTPException(422, str(e)) from e
    except service.Conflict as e:
        raise HTTPException(409, str(e)) from e
    xp = game.xp_for_refs(db, sources=("set", "pr"), ref_id=row.id)
    unlocks = [UnlockedStep(**u.model_dump()) for u in skills.unlocks_for_set(db, row.id)]
    return LoggedSet(
        set=service.set_out(row), xp_awarded=xp, previous_best_e1rm=previous, unlocks=unlocks
    )


@router.post("/{workout_id}/finish", response_model=FinishedWorkout)
def finish(
    workout_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> FinishedWorkout:
    try:
        workout, minutes, hard = service.finish_workout(db, bus, workout_id, now)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Conflict as e:
        raise HTTPException(409, str(e)) from e
    xp = game.xp_for_refs(db, sources=("session",), ref_id=workout.id)
    return FinishedWorkout(
        workout=service.workout_out(workout), xp_awarded=xp, active_minutes=minutes, hard_sets=hard
    )


@router.patch("/{workout_id}/sets/{set_id}", response_model=SetOut)
def edit_set(
    workout_id: int,
    set_id: int,
    body: SetPatch,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
) -> SetOut:
    """Fix a logged set. PRs for the exercise and the set's muscle load are re-derived.
    If the set is no longer a PR its PR XP is reversed (a new row in the append-only
    ledger); an edit never pays XP."""
    try:
        row = service.update_set(db, bus, workout_id, set_id, body)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    except service.Invalid as e:
        raise HTTPException(422, str(e)) from e
    return service.set_out(row)


@router.delete("/{workout_id}/sets/{set_id}", status_code=204)
def delete_set(
    workout_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
) -> Response:
    try:
        service.delete_set(db, bus, workout_id, set_id)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=204)
