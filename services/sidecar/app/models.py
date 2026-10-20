"""Import every module's ORM models so Base.metadata is complete (used by Alembic)."""

from app.core import outbox_models  # noqa: F401
from app.core.db import Base
from app.modules.gamification import models as gamification_models  # noqa: F401
from app.modules.nutrition import models as nutrition_models  # noqa: F401
from app.modules.progress import models as progress_models  # noqa: F401
from app.modules.workouts import models as workouts_models  # noqa: F401

__all__ = ["Base"]
