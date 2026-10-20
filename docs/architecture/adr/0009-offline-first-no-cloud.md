# ADR-0009: Offline-First, No Cloud, No Accounts

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

The owner asked for a desktop app with local storage and "no need for cloud". The
data is health data and body photos. The team has no budget for servers, and cloud free tiers
expire. India's DPDP Act adds duties for
anyone who processes personal data.

## Decision

ASCEND has **no backend server, no accounts, no sync and no telemetry**.

- All data in `%APPDATA%\ASCEND` (SQLite + files).
- Allowed network calls, both opt-in and switchable off: **model downloads** and the
  **update check** against GitHub Releases. Nothing else.
- A CI test runs the packaged E2E journey with egress blocked and fails on any
  non-localhost connection attempt.
- Features that need a server are cut or replaced (online leaderboards → ghost races).
- Wearable data comes in only as **files** the user exports (GPX/FIT/Health Connect/Apple Health) — later.

## Consequences

### Positive

- Privacy by design; nothing to breach on a server.
- Zero hosting cost; works on trains, in gyms without signal.
- Simpler legal position: the team never receives user data.

### Negative / Trade-offs

- No multi-device sync, no social features, no remote crash reports (users export diagnostics manually).
- No live wearable sync from a Windows-only app.
- Updates rely on users opening the app with internet occasionally.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Cloud backend (Supabase/Firebase) as in the earlier web prototype | Contradicts the requirement; cost and DPDP duties. |
| Optional cloud sync | Real but large scope; parked until after v1.2 with its own ADR and privacy review. |
| Anonymous telemetry | Even anonymous health-app telemetry needs consent and a server; not worth it. |
