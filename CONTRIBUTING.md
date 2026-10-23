# Contributing to ASCEND

Team: **Navin** (lead, MLOps), **Gokul** (DevOps), **Jegatheesan** (backend), **Dhanush** (frontend).
`.github/CODEOWNERS` maps folders to reviewers.

## Setup

See the [README quick start](README.md#developer-quick-start). Then install the git hooks once:

```bash
uv tool install pre-commit   # or: pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

## Branches

- `main` is always releasable; CI must be green. Never push to `main` directly.
- Branch per change: `feat/muscle-drilldown`, `fix/quest-streak`, `ci/cache-uv`, `docs/adr-0007`.
- Keep branches short-lived (a day or two). Rebase on `main` before opening the PR.

## Commits: Conventional Commits

```
<type>(<scope>): <what changed, imperative, lower case>
```

| type | use for |
|---|---|
| `feat` | a user-visible feature |
| `fix` | a bug fix |
| `test` | tests only |
| `refactor` | code change with no behaviour change |
| `docs` | documentation only |
| `ci` | GitHub Actions |
| `build` | packaging, Docker, PyInstaller, electron-builder |
| `chore` | tooling, dependencies, housekeeping |
| `style` | formatting only |

Scopes: `sidecar`, `workouts`, `nutrition`, `gamification`, `progress`, `coach`, `db`,
`desktop`, `shared`, `ml`, `docker`. Example: `feat(nutrition): add katori portion presets`.

Small commits are better than big ones: one logical change each, tests included.

## Pull requests

1. Fill in what and why; link the issue.
2. `make lint typecheck test` passes locally.
3. New logic has tests: engines get unit tests, endpoints get API tests (`TestClient`).
4. Changed a formula (XP, load, TDEE...)? Bump its `FORMULA_VERSION` and say why in the PR.
5. Changed the database? Add an Alembic migration (`uv run alembic revision --autogenerate -m "..."`),
   read the generated file, and never edit a migration that is already on `main`.
6. One approving review from the CODEOWNER of the area; the author merges with **squash**.

## Code rules

- **The app must work with AI off.** Numbers come from deterministic engines; the coach only explains.
- **No network calls** except to `127.0.0.1` (Ollama). No telemetry, no analytics.
- Modules talk through the **event bus** for side effects (see `services/sidecar/app/core/events.py`);
  read-only queries may call another module's `service` functions.
- Mark estimates as estimates in the UI (TDEE, calorie burn, food values).
- Python: typed, ruff-clean, docstrings on public functions with units in formulas.
- TypeScript: `strict`, no `any` unless commented why.
