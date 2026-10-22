"""HTTP API of the intelligence layer: the engines' outputs with their inputs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.intelligence import (
    diet_service,
    explain,
    insights,
    notices,
    personal,
    progression_service,
    recovery_service,
    tdee,
)
from app.modules.intelligence import progression as prog
from app.modules.intelligence import recovery as rec
from app.modules.intelligence.schemas import (
    CheckinUsed,
    DecisionIn,
    DecisionOut,
    E1rmOut,
    E1rmPoint,
    ExplanationOut,
    InsightCheckOut,
    InsightFindingOut,
    InsightsOut,
    MuscleRecoveryOut,
    NoticeOut,
    RecoveryGroupOut,
    RecoveryOut,
    SkillGoalOut,
    StalledLiftOut,
    TargetOut,
    TdeeOut,
    TdeePointOut,
    TdeeWeekOut,
    TopSet,
    Why,
)
from app.modules.progress.taxonomy import MUSCLE_BY_KEY
from app.modules.workouts.models import Exercise

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


def _muscle_out(m: rec.MuscleRecovery) -> MuscleRecoveryOut:
    prior = MUSCLE_BY_KEY[m.key].half_life_h
    return MuscleRecoveryOut(
        key=m.key,
        label=m.label,
        group=m.group,
        status=m.status,
        readiness=m.readiness,
        readiness_population=m.readiness_population,
        fatigue=m.fatigue,
        capacity=m.capacity,
        half_life_h=m.half_life_h,
        prior_half_life_h=prior,
        k=m.k,
        modifier=m.modifier,
        es_7d=m.es_7d,
        ready_at=m.ready_at,
        last_trained=m.last_trained,
        top_sets=[TopSet(exercise=e, dose_now=v, hours_ago=h) for e, v, h in m.top_sets],
        why=Why(
            formula="readiness = 1 - min(1, M x F / C), F = sum of ES x 2^(-hours / (h x k))",
            inputs={
                "fatigue_F": m.fatigue,
                "capacity_C": m.capacity,
                "prior_half_life_h": prior,
                "personal_k": m.k,
                "half_life_h": m.half_life_h,
                "checkin_M": m.modifier,
                "readiness": m.readiness,
                "readiness_population": m.readiness_population,
            },
        ),
    )


@router.get("/recovery", response_model=RecoveryOut)
def recovery(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> RecoveryOut:
    """recovery-v2 per muscle with every input of its readiness, the check-in used and the
    personal factor per muscle group (population value 1 until there is evidence)."""
    states = recovery_service.states(db, now)
    params = recovery_service.params(db)
    checkin = recovery_service.checkin_for(db, now)
    groups = []
    for g in rec.GROUPS:
        row = params.get(g)
        groups.append(
            RecoveryGroupOut(
                group=g,
                k=row.k if row else 1.0,
                k_low=row.k_low if row else 1.0,
                k_high=row.k_high if row else 1.0,
                n=row.n if row else 0,
                personal=bool(row.personal) if row else False,
                alpha=row.alpha if row else None,
                updated_at=row.updated_at if row else None,
            )
        )
    return RecoveryOut(
        algo_version=f"{rec.ALGO_VERSION}+{personal.ALGO_VERSION}",
        formula=rec.formula(),
        checkin=CheckinUsed(sleep=checkin.sleep, soreness=checkin.soreness) if checkin else None,
        groups=groups,
        muscles=[_muscle_out(m) for m in states],
    )


# --- progression -------------------------------------------------------------------------


def _unit(e: Exercise, t: prog.Target) -> Literal["kg", "reps", "s"]:
    if e.measure == "hold":
        return "s"
    series_loaded = t.inputs.get("last_load_kg")
    return "kg" if isinstance(series_loaded, (int, float)) and series_loaded > 0 else "reps"


def target_out(db: Session, e: Exercise, t: prog.Target, now: datetime) -> TargetOut:
    kept = progression_service.kept_at(db, e.id, now)
    unit = _unit(e, t)
    inputs = dict(t.inputs)
    readiness = t.facts.get("readiness_pct")
    track = t.e1rm
    return TargetOut(
        exercise_id=e.id,
        exercise=e.name,
        kind=t.kind,
        sets=t.sets,
        reps=t.reps,
        seconds=t.seconds,
        weight_kg=t.weight_kg,
        rpe=t.rpe,
        change=t.change,
        reason=t.reason,
        why=t.why,
        explanation=Why(formula=t.formula, inputs=inputs),
        rep_range=list(t.rep_range) if t.rep_range else None,
        increment_kg=t.increment_kg,
        e1rm=(
            E1rmOut(
                unit=unit,
                current=track.current,
                best=track.best,
                last=track.last,
                trend_pct_week=track.trend_pct_week,
                series=[E1rmPoint(at=a, value=v) for a, v in track.series],
            )
            if track is not None and track.series
            else None
        ),
        stalled=t.stall.stalled,
        stall_sessions=t.stall.sessions_flat,
        skill=(
            SkillGoalOut(
                skill_name=t.skill.skill_name,
                step_name=t.skill.step_name,
                criterion=t.skill.describe(),
                sessions_met=t.skill.sessions_met,
                confirm_sessions=t.skill.confirm_sessions,
            )
            if t.skill
            else None
        ),
        readiness=float(readiness) / 100 if isinstance(readiness, (int, float)) else None,
        kept_until=kept + timedelta(days=prog.KEEP_DAYS) if kept else None,
        deload_week=t.reason == "deload_week",
        algo_version=t.algo_version,
    )


def _target(db: Session, exercise_id: int, now: datetime) -> tuple[Exercise, prog.Target]:
    try:
        return progression_service.next_target(db, exercise_id, now)
    except progression_service.ExerciseMissing as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/progression/{exercise_id}", response_model=TargetOut)
def progression_target(
    exercise_id: int, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> TargetOut:
    """prog-v1: the next session's target for one exercise, with the reason, a one-line
    why, the formula and every input."""
    e, t = _target(db, exercise_id, now)
    return target_out(db, e, t, now)


@router.post("/progression/{exercise_id}/decision", response_model=DecisionOut, status_code=201)
def progression_decision(
    exercise_id: int,
    body: DecisionIn,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> DecisionOut:
    """Record "use it" or "keep mine" for the current target. "Keep mine" stops new
    targets for this exercise for 7 days (FT-1)."""
    _, t = _target(db, exercise_id, now)
    row = progression_service.decide(db, exercise_id, body.choice, now, t)
    return DecisionOut(
        id=row.id,
        exercise_id=exercise_id,
        decided_at=row.decided_at,
        choice=row.choice,
        reason=row.reason,
        kept_until=row.decided_at + timedelta(days=prog.KEEP_DAYS)
        if row.choice == "kept"
        else None,
        algo_version=row.algo_version,
    )


@router.get("/stalls", response_model=list[StalledLiftOut])
def stalls(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> list[StalledLiftOut]:
    """Exercises trained in the last 14 days with no rep record in 3 sessions (prog-v1)."""
    out = []
    for e, t in progression_service.stalled_lifts(db, now):
        out.append(
            StalledLiftOut(
                exercise_id=e.id,
                exercise=e.name,
                sessions_flat=t.stall.sessions_flat,
                best=t.stall.cycle_best,
                unit=_unit(e, t),
            )
        )
    return out


# --- explanations (ADR-0016) -----------------------------------------------------------------


def _explanation_out(e: explain.Explanation) -> ExplanationOut:
    return ExplanationOut(
        text=e.text,
        template=e.template,
        phrasing="model" if e.phrasing == "model" else "template",
        model=e.model,
        fallback=e.fallback,
        checks=e.checks,
        facts=e.facts,
        version=e.version,
    )


@router.get("/progression/{exercise_id}/explanation", response_model=ExplanationOut)
def progression_explanation(
    exercise_id: int,
    request: Request,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> ExplanationOut:
    """The target's "why" in plain words: the local model's sentence when it passes the
    number and phrase checks, else the template."""
    e, t = _target(db, exercise_id, now)
    facts = explain.target_facts(t)
    key = ("target", str(e.id), f"{t.reason}:{t.weight_kg}:{t.reps}:{t.seconds}:{t.sets}")
    return _explanation_out(explain.explain(db, request.app.state.settings, key, t.why, facts))


@router.get("/recovery/{muscle}/explanation", response_model=ExplanationOut)
def recovery_explanation(
    muscle: str,
    request: Request,
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> ExplanationOut:
    """One muscle's readiness in plain words (same guard and fallback)."""
    m = next((s for s in recovery_service.states(db, now) if s.key == muscle), None)
    if m is None:
        raise HTTPException(404, f"unknown muscle '{muscle}'")
    template, facts = explain.muscle_template(m)
    key = ("muscle", m.key, f"{m.readiness}:{m.fatigue}:{m.k}:{m.modifier}")
    return _explanation_out(explain.explain(db, request.app.state.settings, key, template, facts))


@router.get("/notices", response_model=list[NoticeOut])
def system_notices(
    db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> list[NoticeOut]:
    """The System's current notices, most important first (at most one of each kind)."""
    return [
        NoticeOut(id=n.id, code=n.code, title=n.title, text=n.text, at=n.at)  # type: ignore[arg-type]
        for n in notices.current(db, now)
    ]


# --- diet: adaptive TDEE and weekly insights (ADR-0018, ADR-0019) ----------------------------

TDEE_FORMULA = (
    "Kalman filter on [trend weight W, expenditure T]: overnight W += (intake - T) / 7700; "
    "a morning weigh-in corrects W and, through their covariance, T. "
    "Prior T = Mifflin-St Jeor BMR x activity factor (SD 450 kcal). "
    "Weekly target = T at the end of last week + goal adjustment, changed only after "
    f"{tdee.GATE_DAYS}+ logged days, {tdee.WEIGH_IN_GATE}+ weigh-ins and a settled estimate, "
    f"by at most {tdee.MAX_WEEKLY_CHANGE_KCAL} kcal a week. "
    "T is read from the intake you log: if meals are under-logged, T is the expenditure that "
    "matches what is logged, which is what a target in logged calories needs."
)


def _tdee_or_404(db: Session, now: datetime) -> tdee.TdeeResult:
    report = diet_service.tdee_report(db, now.date())
    if report is None:
        raise HTTPException(404, "Set up your profile first")
    return report


def _tdee_template(r: tdee.TdeeResult) -> tuple[str, dict[str, float | int | str]]:
    facts: dict[str, float | int | str] = {
        "tdee_kcal": round(r.tdee_kcal),
        "range_low_kcal": round(r.low_kcal),
        "range_high_kcal": round(r.high_kcal),
        "formula_tdee_kcal": round(r.prior_tdee_kcal),
        "weekly_target_kcal": r.target_kcal,
        "weigh_ins": r.weigh_ins,
        "intake_days_last_7": r.intake_days_7,
    }
    text = (
        f"You burn about {round(r.tdee_kcal)} kcal a day (likely {round(r.low_kcal)} to "
        f"{round(r.high_kcal)}), estimated from {r.weigh_ins} weigh-ins and your logged meals; "
        f"the formula alone said {round(r.prior_tdee_kcal)}. This week's target is "
        f"{r.target_kcal} kcal."
    )
    if r.paused:
        text += f" Meals were logged on {r.intake_days_7} of the last 7 days, so the target holds."
    return text, facts


@router.get("/tdee", response_model=TdeeOut)
def tdee_estimate(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    now: datetime = Depends(get_now),
) -> TdeeOut:
    """tdee-v1: expenditure ± SD, trend weight, the weekly target and the last `days` days."""
    r = _tdee_or_404(db, now)
    return TdeeOut(
        algo_version=r.algo_version,
        status=r.status,  # type: ignore[arg-type]
        tdee_kcal=r.tdee_kcal,
        sd_kcal=r.sd_kcal,
        low_kcal=round(r.low_kcal, 1),
        high_kcal=round(r.high_kcal, 1),
        formula_tdee_kcal=r.prior_tdee_kcal,
        formula_target_kcal=r.formula_target_kcal,
        target_kcal=r.target_kcal,
        target_source=r.target_source,  # type: ignore[arg-type]
        target_week_start=r.target_week_start,
        trend_kg=r.trend_kg,
        days_of_data=r.days_of_data,
        weigh_ins=r.weigh_ins,
        intake_days_7=r.intake_days_7,
        weigh_ins_7=r.weigh_ins_7,
        gate_days=tdee.GATE_DAYS,
        paused=r.paused,
        reason=r.reason,
        series=[
            TdeePointOut(
                day=s.day,
                weight_kg=s.weight_kg,
                intake_kcal=s.intake_kcal,
                intake_used=s.intake_used,
                trend_kg=s.trend_kg,
                tdee_kcal=s.tdee_kcal,
                sd_kcal=s.sd_kcal,
            )
            for s in r.series[-days:]
        ],
        weeks=[
            TdeeWeekOut(
                week_start=w.week_start,
                target_kcal=w.target_kcal,
                tdee_kcal=w.tdee_kcal,
                sd_kcal=w.sd_kcal,
                intake_days=w.intake_days,
                changed=w.changed,
                from_estimate=w.from_estimate,
                reason=w.reason,
            )
            for w in r.weeks[-12:]
        ],
        why=Why(
            formula=TDEE_FORMULA,
            inputs={
                "tdee_kcal": r.tdee_kcal,
                "sd_kcal": r.sd_kcal,
                "formula_tdee_kcal": r.prior_tdee_kcal,
                "trend_kg": r.trend_kg,
                "weigh_ins": r.weigh_ins,
                "days_of_data": r.days_of_data,
                "intake_days_7": r.intake_days_7,
                "gate_days": tdee.GATE_DAYS,
                "weekly_target_kcal": r.target_kcal,
                "target_source": r.target_source,
                "status": r.status,
            },
        ),
    )


@router.get("/tdee/explanation", response_model=ExplanationOut)
def tdee_explanation(
    request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ExplanationOut:
    """The expenditure estimate in plain words (local model behind the coach guard, else
    the template)."""
    r = _tdee_or_404(db, now)
    template, facts = _tdee_template(r)
    key = ("tdee", now.date().isoformat(), f"{r.tdee_kcal}:{r.sd_kcal}:{r.target_kcal}")
    return _explanation_out(explain.explain(db, request.app.state.settings, key, template, facts))


def _insights_or_404(db: Session, now: datetime) -> insights.InsightReport:
    out = diet_service.insight_report(db, now.date())
    if out is None:
        raise HTTPException(404, "Set up your profile first")
    return out[0]


@router.get("/insights", response_model=InsightsOut)
def diet_insights(db: Session = Depends(get_db), now: datetime = Depends(get_now)) -> InsightsOut:
    """insights-v1: at most three findings for the last 7 complete days, each with a Why."""
    rep = _insights_or_404(db, now)
    return InsightsOut(
        algo_version=rep.algo_version,
        week_end=rep.week_end,
        findings=[
            InsightFindingOut(
                code=f.code,
                title=f.title,
                text=f.text,
                severity=f.severity,
                numbers=f.numbers,
                why=Why(formula=f.formula, inputs=f.inputs),
            )
            for f in rep.findings
        ],
        checks=[
            InsightCheckOut(code=c.code, outcome=c.outcome, detail=c.detail)  # type: ignore[arg-type]
            for c in rep.checks
        ],
    )


@router.get("/insights/{code}/explanation", response_model=ExplanationOut)
def insight_explanation(
    code: str, request: Request, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> ExplanationOut:
    """One finding in plain words (local model behind the coach guard, else its own text)."""
    rep = _insights_or_404(db, now)
    f = next((x for x in rep.findings if x.code == code), None)
    if f is None:
        raise HTTPException(404, f"No {code} finding this week")
    facts = {k: v for k, v in f.inputs.items() if v is not None}
    key = ("insight", f.code, f"{rep.week_end.isoformat()}:{sorted(facts.items())}")
    return _explanation_out(explain.explain(db, request.app.state.settings, key, f.text, facts))
