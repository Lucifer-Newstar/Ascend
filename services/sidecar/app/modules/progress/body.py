"""Body metrics (weigh-ins) and tape measurements."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.progress import trend
from app.modules.progress.models import BodyMetric, Measurement
from app.modules.progress.schemas import (
    BodyMetricIn,
    BodyMetricOut,
    EtaOut,
    MeasurementIn,
    MeasurementOut,
)


def _all_metrics(db: Session) -> list[BodyMetric]:
    return list(db.scalars(select(BodyMetric).order_by(BodyMetric.measured_at)).all())


def list_metrics(db: Session, now: datetime, days: int) -> list[BodyMetricOut]:
    """Weigh-ins in the window, oldest first, each with its trend weight.

    The trend is computed over the whole history so the first point in the
    window is not reset to its raw weight."""
    rows = _all_metrics(db)
    trends = trend.smooth([(r.measured_at, r.weight_kg) for r in rows])
    since = now - timedelta(days=days)
    return [
        BodyMetricOut(
            id=r.id,
            measured_at=r.measured_at,
            weight_kg=r.weight_kg,
            trend_kg=t,
            waist_cm=r.waist_cm,
            resting_hr=r.resting_hr,
        )
        for r, t in zip(rows, trends, strict=True)
        if r.measured_at >= since
    ]


def log_metric(db: Session, data: BodyMetricIn, now: datetime) -> BodyMetricOut:
    row = BodyMetric(
        measured_at=(data.measured_at or now).replace(microsecond=0),
        weight_kg=data.weight_kg,
        waist_cm=data.waist_cm,
        resting_hr=data.resting_hr,
    )
    db.add(row)
    db.flush()
    rows = _all_metrics(db)
    trends = trend.smooth([(r.measured_at, r.weight_kg) for r in rows])
    t = dict(zip([r.id for r in rows], trends, strict=True))[row.id]
    return BodyMetricOut(
        id=row.id,
        measured_at=row.measured_at,
        weight_kg=row.weight_kg,
        trend_kg=t,
        waist_cm=row.waist_cm,
        resting_hr=row.resting_hr,
    )


def delete_metric(db: Session, metric_id: int) -> bool:
    row = db.get(BodyMetric, metric_id)
    if row is None:
        return False
    db.delete(row)
    return True


def latest_weight(db: Session) -> float | None:
    row = db.scalars(select(BodyMetric).order_by(BodyMetric.measured_at.desc())).first()
    return row.weight_kg if row else None


def log_measurement(db: Session, data: MeasurementIn, now: datetime) -> MeasurementOut:
    previous = db.scalars(
        select(Measurement)
        .where(Measurement.site == data.site)
        .order_by(Measurement.measured_at.desc())
    ).first()
    row = Measurement(
        measured_at=(data.measured_at or now).replace(microsecond=0), site=data.site, cm=data.cm
    )
    db.add(row)
    db.flush()
    out = MeasurementOut.model_validate(row)
    out.change_cm = round(row.cm - previous.cm, 1) if previous else None
    return out


def list_measurements(db: Session, site: str | None = None) -> list[MeasurementOut]:
    stmt = select(Measurement).order_by(Measurement.site, Measurement.measured_at)
    if site:
        stmt = stmt.where(Measurement.site == site)
    out: list[MeasurementOut] = []
    last: dict[str, float] = {}
    for r in db.scalars(stmt).all():
        m = MeasurementOut.model_validate(r)
        m.change_cm = round(r.cm - last[r.site], 1) if r.site in last else None
        last[r.site] = r.cm
        out.append(m)
    return out


def eta_for(db: Session, goal_kg: float | None, now: datetime) -> EtaOut:
    rows = _all_metrics(db)
    e = trend.eta([(r.measured_at, r.weight_kg) for r in rows], goal_kg, now.date())
    return EtaOut(
        goal_kg=e.goal_kg,
        current_trend_kg=e.current_trend_kg,
        rate_kg_per_week=e.rate_kg_per_week,
        eta_from=e.eta_from,
        eta_to=e.eta_to,
        confidence=e.confidence,
        on_track=e.on_track,
        reason=e.reason,
        formula_version=trend.FORMULA_VERSION,
    )
