"""foods_v12: about 150 more common Indian and student foods (v1.2).

Revision ID: 0026
Revises: 0025

Data only: rows are added to the reference food table, nothing the user logged is touched.
A name already in the table (including a food the user added themselves) is skipped. The
downgrade removes the added foods that no logged meal refers to.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.modules.nutrition.seed_v12 import FOODS_V12, SOURCE

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

foods = sa.table(
    "foods",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("portion_label", sa.String),
    sa.column("portion_g", sa.Float),
    sa.column("kcal", sa.Float),
    sa.column("protein_g", sa.Float),
    sa.column("carbs_g", sa.Float),
    sa.column("fat_g", sa.Float),
    sa.column("source", sa.String),
)


def upgrade() -> None:
    bind = op.get_bind()
    have = {row[0].lower() for row in bind.execute(sa.select(foods.c.name))}
    rows = [
        {
            "name": n,
            "portion_label": label,
            "portion_g": g,
            "kcal": kcal,
            "protein_g": p,
            "carbs_g": c,
            "fat_g": f,
            "source": SOURCE,
        }
        for n, label, g, kcal, p, c, f in FOODS_V12
        if n.lower() not in have
    ]
    if rows:
        op.bulk_insert(foods, rows)


def downgrade() -> None:
    bind = op.get_bind()
    names = [n for n, *_ in FOODS_V12]
    used = {row[0] for row in bind.execute(sa.text("SELECT DISTINCT food_id FROM meal_items"))}
    ids = [
        row[0]
        for row in bind.execute(
            sa.select(foods.c.id).where(foods.c.name.in_(names), foods.c.source == SOURCE)
        )
        if row[0] not in used
    ]
    if ids:
        bind.execute(foods.delete().where(foods.c.id.in_(ids)))
