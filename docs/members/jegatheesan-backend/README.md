# Jegatheesan K — Backend Developer

> **Member 2** — Backend track: the Python sidecar, every engine, the database and the
> integration with local AI.

## Role

Own the sidecar: a FastAPI modular monolith that stores everything in SQLite, turns sets
and meals into numbers through deterministic engines, and talks to Ollama for the coach —
with a rules fallback for every AI path.

## Status at 1.0.0 (2026-10-23)

The responsibilities below are the plan from 2026-10-20. What shipped in this area:

- **Delivered:** the FastAPI modular monolith (`workouts`, `nutrition`, `gamification`,
  `progress`, `skills`, `intelligence`, `coach`, `io`) with SQLite in WAL mode, 19 Alembic
  migrations, the event bus with a transactional outbox, token and Host checks; the deterministic
  engines (recovery-v2, prog-v1, tdee-v1, insights-v1, programs-v1, boss-v1, XP, quests, streaks,
  ranks); the Ollama client with timeouts and the coach's number guard; Strong, Hevy, JSON and CSV
  import/export and `.ascendbak` backups with daily snapshots.
- **Planned here, not in 1.0.0:** the GPU/CPU job queue and the model manager runtime (no model
  downloads), the meal-scan pipeline, the Open Food Facts import, the injury and red-flag coach
  flows and structured logging.

## Primary responsibilities

- Sidecar core: config, DB (WAL pragmas), Alembic migrations, security middleware,
  event bus → transactional outbox, job queue (GPU + CPU workers), structured logging
- Engines (from Navin's specs): muscle load + readiness, progression + deloads, PR
  detection, XP/levels/quests/streaks/ranks, energy targets + adaptive TDEE, ETA
- **Ollama integration:** client with timeouts and streaming, model manager runtime
  (manifest, verified downloads, tiers, GPU lock), fallbacks and templates
- Coach rules: planner, injury protocol, red-flag routing, weekly review, number-fidelity check
- Nutrition: INDB/IFCT/Open Food Facts import, portions, scan pipeline (classifier first → portion → DB; optional VLM second opinion, [ADR-0012](../../architecture/adr/0012-classifier-first-meal-scan.md))
- Import/export adapters (Strong, Hevy, JSON, CSV, `.ascendbak`)
- OpenAPI contracts (owner) and their implementation

## Repo areas owned

- `services/sidecar/` (all)
- `docs/contracts/*.yaml`, `docs/contracts/manifest.json`, `docs/architecture/data-model.md`
- `docs/members/jegatheesan-backend/` (this folder)

## Contracts I provide

| Contract | Consumers | Available |
|---|---|---|
| OpenAPI per module (+ Prism mock) | Dhanush | Phase 0–2 (freeze table in [phases.md §5](../../planning/phases.md#5-contract-freezes)) |
| SSE events | Dhanush | Phase 1 |
| Corrections export format | Navin | Phase 2 (format), Phase 5 (UI) |
| Prediction/confidence logging | Navin | Phase 5 |

## Contracts I consume

| Contract | Provided by | Available |
|---|---|---|
| Formula specs + worked examples | Navin | Phase 1 week 1 |
| `classifier.onnx` + `labels.json` + preprocessing contract | Navin | Phase 2 |
| Sidecar launch protocol | Dhanush | Phase 0 (exists) |
| CI, fixture DB job, packaging constraints | Gokul | Phase 0–1 |

## My commitments

- No engine depends on a model; every formula has golden tests and an `ALGO_VERSION`.
- Every migration is tested from every released schema and preceded by a backup.
- The coach never changes a plan directly — only proposals.
- I can explain the outbox, the job queue and the GPU lock in an interview.
