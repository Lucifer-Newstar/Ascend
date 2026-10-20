"""Food search and meal logging. Publishes MealLogged for gamification."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.events import EventBus, MealLogged
from app.modules.nutrition.models import Food, Meal, MealItem
from app.modules.nutrition.schemas import MealIn, MealOut, Totals


class NotFound(Exception):
    pass


def search_foods(db: Session, q: str = "", limit: int = 50) -> list[Food]:
    stmt = select(Food).order_by(Food.name).limit(limit)
    if q:
        stmt = stmt.where(Food.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt).all())


def log_meal(db: Session, bus: EventBus, data: MealIn, now: datetime) -> Meal:
    meal = Meal(day=now.date(), meal_type=data.meal_type, logged_at=now)
    for item in data.items:
        food = db.get(Food, item.food_id)
        if food is None:
            raise NotFound(f"food {item.food_id} not found")
        p = item.portions
        meal.items.append(MealItem(
            food_id=food.id, food_name=food.name, portions=p,
            kcal=round(food.kcal * p, 1), protein_g=round(food.protein_g * p, 1),
            carbs_g=round(food.carbs_g * p, 1), fat_g=round(food.fat_g * p, 1),
        ))
    db.add(meal)
    db.flush()
    bus.publish(db, MealLogged(meal_id=meal.id, day=meal.day))
    return meal


def get_meal(db: Session, meal_id: int) -> Meal:
    meal = db.get(Meal, meal_id)
    if meal is None:
        raise NotFound(f"meal {meal_id} not found")
    return meal


def delete_meal(db: Session, meal_id: int) -> None:
    db.delete(get_meal(db, meal_id))
    db.flush()


def meals_on(db: Session, day: date) -> list[Meal]:
    return list(db.scalars(select(Meal).where(Meal.day == day).order_by(Meal.logged_at)).all())


def meal_count(db: Session, day: date) -> int:
    return int(db.scalar(select(func.count(Meal.id)).where(Meal.day == day)) or 0)


def day_totals(db: Session, day: date) -> Totals:
    row = db.execute(
        select(
            func.coalesce(func.sum(MealItem.kcal), 0), func.coalesce(func.sum(MealItem.protein_g), 0),
            func.coalesce(func.sum(MealItem.carbs_g), 0), func.coalesce(func.sum(MealItem.fat_g), 0),
        ).join(Meal, Meal.id == MealItem.meal_id).where(Meal.day == day)
    ).one()
    return Totals(kcal=round(row[0], 1), protein_g=round(row[1], 1), carbs_g=round(row[2], 1),
                  fat_g=round(row[3], 1))


def meal_out(meal: Meal) -> MealOut:
    return MealOut(
        id=meal.id, day=meal.day, meal_type=meal.meal_type, logged_at=meal.logged_at,
        items=meal.items,  # type: ignore[arg-type]
        kcal=round(sum(i.kcal for i in meal.items), 1),
    )
