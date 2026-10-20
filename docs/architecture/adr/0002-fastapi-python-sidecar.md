# ADR-0002: Python FastAPI Sidecar for Domain Logic and AI

- **Status:** Accepted (lead decision, 2026-10-20; revisit at the Phase 0 kickoff if the team objects)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

The engines (load model, progression, XP, TDEE, ETA), the database layer and all ML
integration (ONNX Runtime, Ollama client, preprocessing shared with training) are
natural in Python. The ML lane (Navin) trains in Python. Electron's main process is
Node. We need a clean boundary that is typed, testable and supervised.

## Decision

Run a **Python 3.12 FastAPI** app (Uvicorn) as a **sidecar process** started and
supervised by Electron main.

- Bound to `127.0.0.1` on a random port, Bearer launch token passed on stdin, `Host` check.
- **Pydantic v2** models are the single source of truth for API schemas; FastAPI emits
  OpenAPI; the TypeScript client types are generated from it.
- Lifecycle (spawn, ready, health, restart with backoff, shutdown) per
  [system-architecture.md §5](../system-architecture.md#5-sidecar-lifecycle).
- Packaged with PyInstaller (ADR-0008). Python 3.12 is used even though the lead's
  machine has 3.14, because ML/packaging libraries lag new Python releases; `uv`
  installs 3.12 side by side.
- Tests: pytest + httpx `TestClient`, Hypothesis for formulas; ruff + mypy in CI.

## Consequences

### Positive

- One language for engines, data and ML; preprocessing code shared with `ml/`.
- FastAPI gives OpenAPI for free → typed frontend client, mock server, drift check.
- The backend owner (Jegatheesan) used FastAPI in AegisDeploy.
- Crash isolation: a sidecar crash does not take down the UI; the supervisor restarts it.

### Negative / Trade-offs

- Two processes to start and package; cold start must stay < 4 s (estimate) — one-folder PyInstaller build helps.
- Localhost HTTP adds a small latency (~1 ms) per call; fine for this app.
- Antivirus false positives on PyInstaller binaries are possible (see integration edge case E2).

## Alternatives Considered

| Option | Why rejected |
|---|---|
| All logic in Node (main process) | Weak ML ecosystem; ONNX/Ollama clients exist but training/preprocessing parity would be lost. |
| Python embedded via a native bridge (e.g. node-calls-python) | Fragile builds on Windows; no process isolation. |
| gRPC instead of REST | Better typing but harder debugging, no browser-friendly tooling, overkill for one client. |
| stdin/stdout JSON-RPC instead of HTTP | No port, but no OpenAPI, no mock server and no SSE; harder to test. |
