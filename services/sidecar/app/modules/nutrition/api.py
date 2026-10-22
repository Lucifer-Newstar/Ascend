from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import get_bus, get_db, get_now
from app.core.events import EventBus
from app.modules.gamification import service as game
from app.modules.intelligence import diet_service
from app.modules.nutrition import service
from app.modules.nutrition.schemas import DayLog, FoodOut, MealIn, MealLoggedOut
from app.modules.progress import service as progress

router = APIRouter(tags=["nutrition"])


@router.get("/foods", response_model=list[FoodOut])
def search_foods(q: str = "", db: Session = Depends(get_db)) -> list[FoodOut]:
    return [FoodOut.model_validate(f) for f in service.search_foods(db, q)]


@router.post("/meals", response_model=MealLoggedOut, status_code=201)
def log_meal(
    body: MealIn,
    db: Session = Depends(get_db),
    bus: EventBus = Depends(get_bus),
    now: datetime = Depends(get_now),
) -> MealLoggedOut:
    try:
        meal = service.log_meal(db, bus, body, now)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    xp = game.xp_for_refs(db, sources=("meal",), ref_id=meal.id)
    return MealLoggedOut(meal=service.meal_out(meal), xp_awarded=xp)


@router.delete("/meals/{meal_id}", status_code=204)
def delete_meal(meal_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        service.delete_meal(db, meal_id)
    except service.NotFound as e:
        raise HTTPException(404, str(e)) from e
    return Response(status_code=204)


@router.get("/meals/day", response_model=DayLog)
def day_log(
    day: date | None = None, db: Session = Depends(get_db), now: datetime = Depends(get_now)
) -> DayLog:
    d = day or now.date()
    profile = progress.get_profile(db)
    energy = progress.energy_for(profile) if profile else None
    # This week's adaptive target once tdee-v1 has set one (ADR-0018), else the formula's.
    target = diet_service.calorie_target(db, d)
    return DayLog(
        day=d,
        meals=[service.meal_out(m) for m in service.meals_on(db, d)],
        totals=service.day_totals(db, d),
        kcal_target=target[0] if target else None,
        kcal_target_source=target[1] if target else None,  # type: ignore[arg-type]
        protein_target_g=energy.protein_target_g if energy else None,
    )
