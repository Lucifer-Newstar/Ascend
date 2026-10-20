from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    portion_label: Mapped[str] = mapped_column(String(30))
    portion_g: Mapped[float] = mapped_column(Float)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(120))


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(12))
    logged_at: Mapped[datetime] = mapped_column(DateTime)
    items: Mapped[list[MealItem]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", lazy="selectin"
    )


class MealItem(Base):
    """Nutrients are snapshotted at log time so later food-table edits don't rewrite history."""

    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"))
    food_name: Mapped[str] = mapped_column(String(80))
    portions: Mapped[float] = mapped_column(Float)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    meal: Mapped[Meal] = relationship(back_populates="items")
