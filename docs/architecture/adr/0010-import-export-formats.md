# ADR-0010: Import/Export Formats (Strong/Hevy CSV, JSON, .ascendbak)

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Jegatheesan K (adapters), Gokul J (CI fixtures), Navin Jairam M (lead)

## Context

Users switching from other loggers bring years of history; users must be able to
leave with all their data. Paywalled or missing exports are a top complaint about
fitness apps. Imports are also an excellent target for golden-file tests in CI.

## Decision

| Direction | Format | Contents |
|---|---|---|
| Import | **Strong CSV** (both the pre- and post-Oct-2025 header variants) | Workouts, sets, RPE, notes |
| Import | **Hevy CSV** | Workouts, sets |
| Import | **ASCEND plan CSV** (documented template) | A user's own plan |
| Export | **CSV** per entity, workouts in **Strong-compatible columns** | Workouts, sets, meals, body metrics |
| Export | **JSON** (one file, documented schema, `schema_version`) | Everything except photos |
| Backup | **`.ascendbak`** = zip of SQLite online-backup snapshot + photos + `manifest.json` with SHA-256 per file; optional AES-256 password | Everything |
| Later | GPX / FIT (cardio), Apple Health `export.xml`, Health Connect export | Read-only import |

- Adapters live in `services/sidecar/app/modules/io/`, one file per format, each with a
  `detect()` and `parse()`; units converted to SI on ingest; imported rows tagged
  `source`.
- Golden fixtures (real exports, anonymised) in `services/sidecar/tests/fixtures/io/`, tested on
  every PR. Strong's column list is from user reports and the Oct 2025 change from its
  changelog — **verify against a real export before freezing**.
- Contract: [contracts/import-export.yaml](../../contracts/import-export.yaml).

## Consequences

### Positive

- Lowers switching cost from Strong/Hevy; users can always leave.
- Backups double as the migration safety net.
- Great CI material: deterministic golden-file tests.

### Negative / Trade-offs

- Third-party formats change without notice; adapters need maintenance.
- Mapping other apps' exercise names to ours needs a fuzzy matcher + user confirmation.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Only our own JSON | Doesn't help switchers; looks like lock-in. |
| Raw SQLite file as the export | Not human-readable; schema-version coupling. |
| Proprietary binary backup | Hard to inspect or recover; zip + manifest is transparent. |
