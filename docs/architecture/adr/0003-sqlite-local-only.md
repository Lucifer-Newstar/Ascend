# ADR-0003: SQLite (WAL, Alembic) as the Only Database

- **Status:** Accepted (lead decision, 2026-10-20; revisit at the Phase 0 kickoff if the team objects)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

All data is local to one Windows user. We need ACID writes, crash safety, simple
backups, zero administration, and a schema that evolves safely across app updates on
machines we will never see.

## Decision

Use **SQLite** in **WAL** mode as the only database, accessed with **SQLAlchemy 2**,
migrated with **Alembic** (batch mode for SQLite `ALTER`s).

- Pragmas: `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`, `busy_timeout=5000`.
- One writer connection pool in the sidecar; workers use the same engine.
- Automatic backup (SQLite online-backup API) before every migration and daily at first idle.
- CI upgrades fixture DBs from every released schema to head.
- Optional encryption via SQLCipher in v1.1.
- Schema: [data-model.md](../data-model.md).

## Consequences

### Positive

- Zero setup for users; one file is easy to back up, export and delete.
- WAL lets the UI read while jobs write.
- The job queue and event outbox live in the same transaction as the data.

### Negative / Trade-offs

- No concurrent multi-process writers (fine: only the sidecar writes).
- SQLite `ALTER TABLE` limits; batch migrations rebuild tables — slower on big tables, acceptable at personal-data scale.
- SQLCipher adds a native dependency to package (v1.1 risk).

## Alternatives Considered

| Option | Why rejected |
|---|---|
| PostgreSQL (embedded or Docker) | Needs a server process or Docker on the user's PC; far too heavy for a desktop app. |
| DuckDB | Excellent for analytics, weaker for many small transactional writes. |
| IndexedDB in the renderer | Keeps data in the sandboxed renderer, away from Python engines; poor migrations story. |
| JSON files | No transactions, no queries; corruption risk on crash. |
