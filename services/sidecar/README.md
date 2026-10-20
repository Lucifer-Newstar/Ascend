# services/sidecar: the ASCEND engine (FastAPI + SQLite)

All of ASCEND's logic and data live in this Python process. The Electron app starts it,
talks to it over `http://127.0.0.1:<random port>` with a per-launch token, and stops it on quit.
It works fully offline; the only optional outbound call is to a local Ollama.

```bash
uv sync                          # Python 3.12 venv + locked deps (uv installs 3.12 if needed)
uv run alembic upgrade head      # create / migrate the database
uv run pytest                    # 95 tests: engines (unit) + API (TestClient)
uv run python -m app --dev       # http://127.0.0.1:8765, token "dev", docs at /docs
uv run python -m app.devtools.seed_demo --wipe   # 2 weeks of demo data (deletes your data!)
```

The interactive API docs (OpenAPI / Swagger UI) are at **http://127.0.0.1:8765/docs** while it runs.
Every endpoint except `/health` and the docs needs `Authorization: Bearer <token>`.

## Layout: a modular monolith

```
app/
  __main__.py          entry point: reads the token from stdin, runs uvicorn
  main.py              create_app(): settings, DB, event bus, routers
  models.py            imports every module's models (for Alembic)
  core/
    config.py          settings from env (ASCEND_PORT, ASCEND_DATA_DIR, OLLAMA_HOST, ...)
    db.py              SQLAlchemy engine with WAL + foreign keys, session per request
    events.py          in-process event bus + domain events
    security.py        bearer-token + Host-header middleware
    migrate.py         runs Alembic programmatically at startup
    deps.py            FastAPI dependencies (db session, bus, clock)
  modules/
    workouts/          exercises, sessions, sets, PR detection (Epley)
    nutrition/         food table, meals, daily totals, TDEE engine
    gamification/      XP ledger, levels, ranks, streaks, daily quests
    progress/          profile, settings, muscle load/recovery, dashboard, history, export
    coach/             rule-based tips + optional Ollama replies
  devtools/seed_demo.py
alembic/versions/      0001 schema, 0002 seed data (exercises + foods)
packaging/             PyInstaller spec for the Windows exe
tests/unit, tests/api
```

Each module has `models.py` (tables), `schemas.py` (Pydantic I/O), `service.py` (use-cases),
`api.py` (routes). **Engines** (`formulas.py`, `streaks.py`, `quests.py`, `muscle_load.py`,
`pr.py`, `tdee.py`, `coach/rules.py`) are pure functions with no database access, so they are
easy to unit-test.

## Event bus

```
POST /workouts/{id}/sets  -> workouts.log_set -> publish SetLogged
    progress.on_set_logged        writes muscle_load_events (effective sets per muscle)
    gamification.on_set_logged    +XP for the set, +40 XP if PR, refresh quest progress
POST /workouts/{id}/finish -> publish WorkoutLogged
    gamification                  session XP (x streak bonus), refresh quests
POST /meals                -> publish MealLogged
    gamification                  meal XP (cap 20/day), refresh quests
```

Handlers run synchronously inside the request's transaction: if anything fails, the set,
its XP and its muscle load all roll back together.

## Formulas (deterministic, versioned)

Every XP row and muscle-load row stores the formula version it was computed with.
All values marked *estimate* are shown as estimates in the UI.

| Engine | Formula | Version |
|---|---|---|
| BMR (estimate) | Mifflin-St Jeor: `10·kg + 6.25·cm − 5·age + (5 male / −161 female)` kcal/day | `tdee-msj-v1` |
| TDEE (estimate) | `BMR × activity factor` (1.2 / 1.375 / 1.55 / 1.725 / 1.9) | |
| Calorie target | `TDEE − 500` (cut) / `+0` / `+300` (bulk), floor 1200 kcal | |
| Protein target | 1.6 g/kg (cut, bulk), 1.4 g/kg (maintain) | |
| e1RM / PR | Epley `kg × (1 + reps/30)`, only for 1–10 reps; PR = strictly above best | `pr-epley-v1` |
| Set XP | 3 (RPE ≥ 7 or no RPE) / 1 (easier) | `xp-v1` |
| Session XP | `20 + 0.5 × active minutes`, session total ≤ 150, × streak bonus | |
| Streak bonus | `× (1 + 0.02 × streak days)`, max × 1.3 | |
| Meal XP | 5 per meal, ≤ 20 per day; PR = 40; daily cap 600 | |
| Level curve | XP from L to L+1 = `round(100 × L^1.3)` | |
| Ranks | E 1–9 · D 10–19 · C 20–34 · B 35–49 · A 50–69 · S 70+ | |
| Streak freezes | earn 1 per 7-day run, hold ≤ 2, auto-used on a missed day | |
| Effort | RPE ≥ 7 or none → 1.0 · 5–6.5 → 0.5 · < 5 → 0.25 | `load-v1` |
| Effective sets | `muscle weight (1.0 / 0.5 / 0.25) × effort`, per set and muscle | |
| Fatigue (estimate) | `Σ ES × 2^(−hours / half-life)`, half-life 24–48 h per muscle | |
| Readiness | `1 − min(1, fatigue / capacity)`, capacity 10 ES (large) / 8 (small) | |
| Status | over if 7-day ES > 1.25 × band top · recovering if readiness < 0.70 · under if below band · else optimal | |
| Burn (estimate) | MET 5.0 × kg × hours of lifting | |

Muscle taxonomy (19 regions, half-lives and weekly bands): `app/modules/progress/taxonomy.py`.

## Database

SQLite at `%APPDATA%\ASCEND\data\ascend.db` (Electron sets `ASCEND_DATA_DIR`), WAL mode,
foreign keys on. Schema changes only through Alembic:

```bash
uv run alembic revision --autogenerate -m "add body measurements"   # then READ the file
uv run alembic upgrade head
```

## Coach

`GET /coach/tip`, `POST /coach/ask`. The rule engine always produces a tip. If AI is enabled
(`PUT /settings`) and Ollama answers on `OLLAMA_HOST` with `qwen3:4b` pulled, the model rewrites
the answer using only the facts the engines computed. On timeout, error or AI off, the
rule-based tip is returned with a `fallback_reason`.

## Packaging

```bash
uv sync --group build
uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm
# -> dist/ascend-sidecar/ascend-sidecar(.exe)
```
