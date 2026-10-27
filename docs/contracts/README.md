# API Contracts — `docs/contracts/`

> **Source of truth for the sidecar's HTTP API and the Electron IPC bridge.**
> Contracts-first: Dhanush's UI builds against a mock server generated from these files,
> Jegatheesan implements against them, Gokul's CI fails if code and contract drift.
> Owner: Jegatheesan (OpenAPI), Dhanush (IPC); reviewer: Navin.

---

## 1. Files

| Contract | Version | Package | Paths | Implemented ops | Planned ops |
|---|---|---|---|---|---|
| [system.yaml](system.yaml) | 0.1.0 | `app.core` | `/events`, `/health`, `/jobs`, `/models`, `/shutdown` | 3 | 4 |
| [workouts.yaml](workouts.yaml) | 0.1.0 | `app.modules.workouts` | `/deload`, `/exercises`, `/plans`, `/prs`, `/workouts` | 23 | 0 |
| [nutrition.yaml](nutrition.yaml) | 0.1.0 | `app.modules.nutrition` | `/foods`, `/meals`, `/scans` | 7 | 6 |
| [gamification.yaml](gamification.yaml) | 0.1.0 | `app.modules.gamification` | `/game` | 10 | 4 |
| [coach.yaml](coach.yaml) | 0.1.0 | `app.modules.coach` | `/coach` | 5 | 7 |
| [progress.yaml](progress.yaml) | 0.1.0 | `app.modules.progress` | `/body-metrics`, `/checkins`, `/dashboard`, `/history`, `/measurements`, `/muscles`, `/profile`, `/progress`, `/settings` | 21 | 0 |
| [import-export.yaml](import-export.yaml) | 0.1.0 | `app.modules.io` | `/backup`, `/data`, `/export`, `/import`, `/restore` | 8 | 1 |
| [skills.yaml](skills.yaml) | 0.1.0 | `app.modules.skills` | `/skills` | 9 | 0 |
| [intelligence.yaml](intelligence.yaml) | 0.1.0 | `app.modules.intelligence` | `/intelligence` | 11 | 0 |
| [planner.yaml](planner.yaml) | 0.1.0 | `app.modules.planner` | `/planner` | 11 | 0 |
| [trainer.yaml](trainer.yaml) | 0.1.0 | `app.modules.trainer` | `/trainer` | 6 | 0 |
| [ai.yaml](ai.yaml) | 0.1.0 | `app.modules.ai` | `/ai` | 3 | 0 |
| [selector.yaml](selector.yaml) | 0.1.0 | `app.modules.selector` | `/selector` | 5 | 0 |
| [actions.yaml](actions.yaml) | 0.1.0 | `app.modules.actions` | `/actions` | 8 | 0 |
| [photos.yaml](photos.yaml) | 0.1.0 | `app.modules.photos` | `/photos` | 6 | 0 |
| [share.yaml](share.yaml) | 0.1.0 | `app.modules.share` | `/share` | 1 | 0 |
| [schedule.yaml](schedule.yaml) | 0.1.0 | `app.modules.schedule` | `/schedule` | 5 | 0 |
| [ml.yaml](ml.yaml) | 0.1.0 | `app.modules.ml` | `/ml` | 4 | 0 |
| [ipc-contract.md](ipc-contract.md) | 1 | `apps/desktop` preload ↔ main | `window.ascend.*` | — | — |
| [manifest.json](manifest.json) | — | module → contract map for the drift check | — | — | — |

Totals (2026-10-27, from the files and `manifest.json`): **146 implemented operations in 18
contracts**, which `make contracts` confirms against the sidecar's OpenAPI, plus 22 planned.

**Status of each operation** is the `x-status` field:

- `implemented` — matches the sidecar's FastAPI OpenAPI exactly; `make contracts`
  (`scripts/check_contract_drift.py`) checks it in CI. The first files were generated from the
  v0.1 skeleton on 2026-10-20; later modules added their own file and a `manifest.json` row.
- `planned` — the agreed v1.0 design. Prism mocks it; the sidecar adds it in the phase
  shown in [features.md](../planning/features.md). Implementing a planned op must not change its shape
  without a contract PR.

All YAML files validate with `openapi-spec-validator` (OpenAPI 3.1).

## 2. Conventions every contract obeys

1. **Base URL** — `http://127.0.0.1:{port}`; the port is random in the app, `8765` with `--dev`.
   Paths are unprefixed (`/workouts`, `/coach/ask`); a version prefix would add nothing for a
   single local client, and the app and sidecar always ship together.
2. **Auth** — every operation needs `Authorization: Bearer <launch token>` except `GET /health`
   (and the schema-only `/docs`, `/openapi.json`). The `Host` header must be `127.0.0.1` or
   `localhost`. Dev token: `dev`.
3. **Errors** — FastAPI's `{"detail": "..."}` with correct status codes (`404`, `409`, `422`).
   Planned operations may add a stable `code` (see the `Error` schema). Messages are safe to
   show the user.
4. **Units** — SI only (kg, cm, seconds, kcal). The UI converts.
5. **Time** — ISO-8601. Day-level fields (`day`, `date`) use the user's day boundary (reset hour).
6. **Long work** — anything that may take more than ~1 s (scan, plan generation, weekly
   review, export, backup, model download) returns `202` with a job and reports through
   `GET /jobs/{id}` and the SSE stream (`GET /events`).
7. **No model-made numbers** — any number in a response comes from an engine (ADR-0005);
   coach text responses say whether they came from the `model` or a `template`/`rules`.
8. **Additive after freeze** — see the freeze table in [phases.md §5](../planning/phases.md#5-contract-freezes).

## 3. Mock server (frontend development)

```bash
# from the repo root
npx @stoplight/prism-cli mock docs/contracts/workouts.yaml -p 4010
# one file per terminal, or merge them first:
npx @redocly/cli join docs/contracts/*.yaml -o build/contracts.yaml
npx @stoplight/prism-cli mock build/contracts.yaml -p 4010
```

Point the renderer at `http://127.0.0.1:4010` with `VITE_SIDECAR_URL` in dev. Prism returns
schema-valid examples, so screens can be built before the backend lands.

## 4. Drift check (CI)

`scripts/check_contract_drift.py` (owner: Gokul) imports `create_app`, reads
`app.openapi()`, and for every row of [manifest.json](manifest.json):

- every implemented operation in the code must exist in the contract with the same
  method, path, parameters, request body and response schemas;
- every operation in the contract marked `implemented` must exist in the code;
- a `planned` operation that appears in the code fails the check until its `x-status`
  is flipped to `implemented` in the same PR.

Error responses (404, 409…) documented in a contract may be missing from the code's
OpenAPI, because FastAPI only lists responses an endpoint declares; an error response the
code declares must be documented. Run it locally with `make contracts`;
`--update-counts` rewrites the counts in manifest.json.

Planned: generated TypeScript types (`openapi-typescript`) checked in the same job. Until
then `packages/shared/src/api.ts` is kept in sync by hand.

## 5. Changing a contract

1. Open a PR that edits the YAML **first** (label `contract`), with an example.
2. Two approvals: the other side of the contract + Navin.
3. Breaking change after freeze → ADR + `feat(<module>)!:` commit.
4. Update [manifest.json](manifest.json) counts and this table.
