# Tracker — through v1.0

> **Status board for phases 0–3.** Updated by the lead after each weekly sync.
> Legend: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked · ➡ moved (see decision log).
> Last updated: 2026-10-20 (planning; nothing started).

---

## 1. Board

| # | Phase | Item | Owner | Status | Evidence (PR / run) |
|---|---|---|---|---|---|
| 1 | 0 | Repo, branch protection, CODEOWNERS, PR template | Navin | ⬜ | — |
| 2 | 0 | pre-commit + CI matrix (windows + ubuntu) | Gokul | ⬜ | — |
| 3 | 0 | Secure Electron shell + typed preload | Dhanush | ⬜ | — |
| 4 | 0 | FastAPI /health + SQLite WAL + Alembic baseline | Jegatheesan | ⬜ | — |
| 5 | 0 | Sidecar supervisor (port, token, health, backoff) | Dhanush | ⬜ | — |
| 6 | 0 | PyInstaller sidecar + NSIS hello-world installer on CI | Gokul | ⬜ | — |
| 7 | 0 | OpenAPI stubs + IPC contract v1 + mock server | Jegatheesan / Dhanush | ⬜ | — |
| 8 | 0 | Docs committed; ADRs ratified | Navin | ⬜ | — |
| 9 | 1 | Sessions/sets API + logger UI | Jegatheesan / Dhanush | ⬜ | — |
| 10 | 1 | Event bus + transactional outbox | Jegatheesan | ⬜ | — |
| 11 | 1 | Muscle-load projector + muscle map component | Jegatheesan / Dhanush | ⬜ | — |
| 12 | 1 | PR detection + History | Jegatheesan / Dhanush | ⬜ | — |
| 13 | 1 | XP, levels, daily quests, streak freezes | Jegatheesan | ⬜ | — |
| 14 | 1 | Rings + onboarding | Dhanush | ⬜ | — |
| 15 | 1 | INDB/IFCT import + portions + food search | Jegatheesan | ⬜ | — |
| 16 | 1 | Coverage gate, contract-drift job, migration upgrade tests | Gokul | ⬜ | — |
| 17 | 1 | DVC + MLflow (Compose); 300 meal photos; baseline run | Navin | ⬜ | — |
| 18 | 2 | Job queue + model manager + Ollama client + fallbacks | Jegatheesan | ⬜ | — |
| 19 | 2 | Coach planner, injury flow, weekly review | Jegatheesan | ⬜ | — |
| 20 | 2 | Chat UI (SSE), scan UI, proposal diffs | Dhanush | ⬜ | — |
| 21 | 2 | Classifier v0 + ONNX parity + eval gate | Navin | ⬜ | — |
| 22 | 2 | Model benchmarks on reference laptop (tokens/s, VRAM) | Navin / Jegatheesan | ⬜ | — |
| 23 | 3 | Release workflow, auto-update, SBOM, checksums | Gokul | ⬜ | — |
| 24 | 3 | Backup/restore, export, Strong/Hevy import, diagnostics | Jegatheesan / Dhanush | ⬜ | — |
| 25 | 3 | States pass + packaged smoke test | Dhanush / Gokul | ⬜ | — |
| 26 | 3 | Rollback drill, release notes, v1.0.0 | Navin | ⬜ | — |

## 2. Summary

| Phase | Items | ✅ | 🟨 | ⬜ | ⛔ |
|---|---|---|---|---|---|
| 0 | 8 | 0 | 0 | 8 | 0 |
| 1 | 9 | 0 | 0 | 9 | 0 |
| 2 | 5 | 0 | 0 | 5 | 0 |
| 3 | 4 | 0 | 0 | 4 | 0 |

## 3. Team hardware (fill at kickoff)

| Member | OS | RAM | GPU / VRAM | Can run local AI tier |
|---|---|---|---|---|
| Navin | Windows 11 | 12 GB | RTX 3050 Laptop / 4 GB | Standard (qwen3:4b) |
| Dhanush | | | | |
| Jegatheesan | | | | |
| Gokul | | | | |

## 4. How to update

1. Change the status cell and add the PR link or CI run in *Evidence*.
2. Moving an item to another phase = ➡ plus a decision-log row.
3. Keep §2 counts in sync (the gate review checks them).
