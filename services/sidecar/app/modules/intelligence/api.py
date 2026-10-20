"""HTTP API of the intelligence layer: the engines' outputs with their inputs."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_now
from app.modules.intelligence import personal, recovery_service
from app.modules.intelligence import recovery as rec
from app.modules.intelligence.schemas import (
    CheckinUsed,
    MuscleRecoveryOut,
    RecoveryGroupOut,
    RecoveryOut,
    TopSet,
    Why,
)
from app.modules.progress.taxonomy import MUSCLE_BY_KEY

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
