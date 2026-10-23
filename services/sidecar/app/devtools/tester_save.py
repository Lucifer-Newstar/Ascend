"""Build a tester save: a backup with a rank-S hunter and everything unlocked (v1.2).

The demo history (a fortnight plus 4 earlier weeks of workouts, meals and check-ins), then
level 72 (rank S), a 45-day streak, 13 lifts with a personal record, all 16 bosses
beaten once (the 12 weekly ones and the 4 seasonal ones) and every theme open. With those,
every wardrobe item unlocks too. The result is an ordinary .ascendbak: copy it into the
app's backups folder and restore it from Settings > Data & backups.

    ASCEND_DATA_DIR=/tmp/ascend-tester uv run python -m app.devtools.tester_save OUT.ascendbak

It wipes ASCEND_DATA_DIR first, so point it at a scratch folder, never at real data (the
demo seeder refuses the installed app's folder).
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import load_settings
from app.core.db import make_engine, make_session_factory
from app.devtools import seed_demo
from app.modules.gamification import boss, themes
from app.modules.gamification.models import BossRaid, XpEvent
from app.modules.io import backup
from app.modules.progress import service as progress
from app.modules.progress.models import BodyMetric


def main() -> None:
    OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ASCEND_tester_save.ascendbak")

    seed_demo.seed(days=14, wipe=True, history_weeks=4)
    settings = load_settings()
    engine = make_engine(settings.resolved_db_url)
    factory = make_session_factory(engine)
    now = datetime.now().replace(microsecond=0)
    today = now.date()

    with factory() as db:
        # PRs on 6 more lifts (10+ in all, for the Katana): one heavy-ish session 3 days ago
        from app.main import build_bus
        from app.modules.workouts import service as workouts
        from app.modules.workouts.models import Exercise
        from app.modules.workouts.schemas import SetIn

        bus = build_bus()
        extra = [
            ("Lateral Raise", 10),
            ("Triceps Pushdown", 30),
            ("Face Pull", 25),
            ("Leg Curl", 40),
            ("Standing Calf Raise", 60),
            ("Hammer Curl", 14),
        ]
        t = datetime.combine(today - timedelta(days=3), time(7, 0))
        w = workouts.start_workout(db, t)
        for name, kg in extra:
            ex = db.scalar(select(Exercise).where(Exercise.name == name))
            if ex is None:
                continue
            for _ in range(3):
                t += timedelta(minutes=3)
                workouts.log_set(
                    db, bus, w.id, SetIn(exercise_id=ex.id, weight_kg=kg, reps=8, rpe=8), t
                )
        workouts.finish_workout(db, bus, w.id, t + timedelta(minutes=5))
        db.commit()

    with factory() as db:
        # 45 days of weigh-ins: a 45-day streak (the demo's own logs fill most days anyway)
        have = {m.date() for m in db.scalars(select(BodyMetric.measured_at)).all()}
        for n in range(0, 45):
            d = today - timedelta(days=n)
            if d not in have:
                db.add(
                    BodyMetric(
                        measured_at=datetime.combine(d, time(7, 15)),
                        weight_kg=round(68.0 + (n % 5) * 0.1, 1),
                    )
                )
        # XP to rank S (level 72) over the last 60 days (never today: the daily cap stays free)
        for n in range(2, 62):
            d = today - timedelta(days=n)
            db.add(
                XpEvent(
                    day=d,
                    at=datetime.combine(d, time(20, 0)),
                    source="tester",
                    ref_id=None,
                    amount=13400,
                    formula_version="tester",
                    note="Tester save: everything unlocked",
                )
            )
        # Every boss beaten once: the 12 weekly ones and the 4 seasonal ones, one per past week
        names = [(n, t) for n, t in boss.BOSSES] + [(s.boss, s.title) for s in boss.SEASONS]
        monday = boss.week_start(today)
        for i, (name, title) in enumerate(names):
            week = monday - timedelta(
                weeks=i + 2
            )  # last week is left to the app (it is settled live)
            raid = db.scalar(select(BossRaid).where(BossRaid.week_start == week))
            if raid is None:
                raid = BossRaid(
                    week_start=week, created_at=datetime.combine(week, time(6, 0)), hp_note=""
                )
                db.add(raid)
            raid.name, raid.title = name, title
            raid.hp, raid.hp_source, raid.hp_note = 12, "starter", "tester save"
            raid.algo_version, raid.tier = boss.ALGO_VERSION, boss.tier_of(name, "expert")
            raid.defeated_at = datetime.combine(week + timedelta(days=3), time(19, 0))
            raid.xp_awarded = 0
        # Every theme open, the demo marker gone (no "wipe the demo?" offer), name it
        progress.set_setting(
            db, themes.UNLOCKED_KEY, json.dumps(sorted(t.key for t in themes.THEMES))
        )
        progress.set_setting(db, "demo_seed", "")
        db.commit()

    with factory() as db:
        from app.modules.gamification import formulas as f
        from app.modules.gamification import service as game

        lvl = f.level_from_total(game.total_xp(db)).level
        st = game.streak(db, today)
        beaten = len(db.scalars(select(BossRaid).where(BossRaid.defeated_at.is_not(None))).all())
        print(
            "level",
            lvl,
            f.rank_for_level(lvl),
            "streak",
            st.current,
            st.best,
            "bosses beaten",
            beaten,
            "themes",
            sorted(themes.unlocked(db, now)),
        )
        print("settings", progress.get_setting(db, "demo_seed", "?"))
        from app.modules.workouts import service as workouts

        print("prs", len(workouts.personal_records(db, None)))

    engine.dispose()
    db_file = settings.data_dir / "ascend.db"
    folder = settings.data_dir / "tester-out"
    folder.mkdir(exist_ok=True)
    info = backup.create_backup(db_file, folder, now)
    shutil.copy(info.path, OUT)
    print("wrote", OUT, info.schema, info.size_bytes)


if __name__ == "__main__":
    main()
