# ADR-0007: Modular Monolith with an In-Process Event Bus

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

Logging one set must update PRs, XP, quest progress, the muscle map and the
dashboard. Four people work in parallel on different domains. AegisDeploy used separate
services and Redis Streams; for a single-user desktop app that is far too heavy.

## Decision

The sidecar is **one process** with domain modules (`workouts`, `nutrition`,
`gamification`, `coach`, `progress`, `io`) plus `core` and `ai`.

- Modules call each other only through `service` interfaces or **events**;
  `import-linter` contracts enforce it in CI.
- **Transactional outbox:** events are written in the same SQLite transaction as the
  data; a dispatcher delivers them after commit and replays on start-up.
- Fast handlers run inline; slow work goes to the **SQLite job queue** (one GPU worker,
  one CPU worker). Handlers are idempotent (`processed_events`).
- Event and job details: [system-architecture.md §8–9](../system-architecture.md#8-event-bus-transactional-outbox).

## Consequences

### Positive

- One binary to package and debug; no broker to install.
- Crash-safe consistency between data and side effects.
- Clear module ownership lets members work in parallel.
- A module could be split out later because boundaries are enforced.

### Negative / Trade-offs

- In-process bus means one slow handler can delay others — slow work must go to jobs.
- Outbox and idempotency add tables and code to test.
- Discipline needed: shortcuts across modules fail CI.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Microservices + Redis/RabbitMQ | Needs extra processes on a user PC; packaging and support burden. |
| Direct function calls everywhere | Tangled modules; crash between write and side effect loses consistency. |
| Python `blinker`/signals without outbox | Not durable; events lost on crash. |
