"""Import every module's ORM models so Base.metadata is complete (used by Alembic)."""

from app.core import outbox_models  # noqa: F401
from app.core.db import Base
from app.modules.actions import models as actions_models  # noqa: F401
from app.modules.gamification import models as gamification_models  # noqa: F401
from app.modules.intelligence import models as intelligence_models  # noqa: F401
from app.modules.nutrition import models as nutrition_models  # noqa: F401
from app.modules.photos import models as photos_models  # noqa: F401
from app.modules.planner import models as planner_models  # noqa: F401
from app.modules.progress import models as progress_models  # noqa: F401
from app.modules.selector import models as selector_models  # noqa: F401
from app.modules.skills import models as skills_models  # noqa: F401
from app.modules.trainer import models as trainer_models  # noqa: F401
from app.modules.workouts import models as workouts_models  # noqa: F401

__all__ = ["Base"]
