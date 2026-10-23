# Roadmap

> Milestone-level view. Phase detail: [phases.md](../planning/phases.md).
> Calendar: [timeline.md](../planning/timeline.md). **All dates are estimates.**
>
> **Outcome (2026-10-23):** the plan below is the design-phase roadmap. The project moved
> faster than planned and released **1.0.0 on 2026-10-23** (versions 0.1.0, 0.2.0 and 0.3.0
> on 2026-10-20, 0.4.0 and 1.0.0 on 2026-10-23). 1.0.0 includes backups, Strong/Hevy import,
> polished states and, from M5, the readiness check-in and adaptive calories; it does not
> include auto-update, diagnostics, meal scan or a trained food classifier. What shipped in each
> version is in the [CHANGELOG](../../CHANGELOG.md).

---

## Milestones

| Milestone | Target (est.) | What exists | Phase |
|---|---|---|---|
| **M0 · Kickoff** | 26 Oct 2026 | Team, roles, repo, rules, docs (this folder) | — |
| **M1 · v0.1 "Hello installer"** | 8 Nov 2026 | Electron shell + supervised sidecar + first migration, CI green, NSIS installer artefact | 0 |
| **M2 · v0.3 "Core loop"** | 13 Dec 2026 | Log a workout → History, PRs, rings, muscle map, XP and quests update; food search | 1 |
| **M3 · v0.6 "Local AI"** | 17 Jan 2027 | Coach plans + injury flow + weekly review, meal scan with corrections, classifier v0 | 2 |
| **M4 · v1.0 "Ship"** | **~7 Feb 2027** | Auto-updating release, backups, diagnostics, Strong/Hevy import, all states polished | 3 |
| **M5 · v1.1 "Breadth"** | 21 Mar 2027 | Martial arts, flexibility, meditation, gallery, progress photos, trials, weekly challenges, readiness check-in, adaptive calories | 4 |
| **M6 · v1.2 "MLOps loop"** | 16 May 2027 | Corrections → retraining → model-only update, drift report, shadow mode | 5 |

## What each milestone proves

| Milestone | Product proof | Engineering proof |
|---|---|---|
| M1 | It installs and starts on Windows | CI on two OSes, packaging from week one |
| M2 | The game loop is fun with real data | Event bus + outbox, migration tests, contract-drift check |
| M3 | AI helps without being required | Job queue, model manager, eval gate, ONNX parity |
| M4 | A stranger can install and use it | Release pipeline, auto-update, SBOM, rollback drill |
| M5 | It covers all 11 sections | E2E + visual regression in CI |
| M6 | It gets smarter from use, locally | Drift signals, retraining, model versioning |

## Beyond v1.2 (not planned, not promised)

Light theme polish, webcam form feedback (MediaPipe), barcode scan, voice input,
wearable file import (GPX/FIT/Health Connect export), female body figure, a Linux build.
