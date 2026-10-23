# Phases

> **Design record, not a description of the shipped app.** Written to plan the build; where it
> differs from the code, the [README](../../README.md) and the [CHANGELOG](../../CHANGELOG.md) describe what
> ASCEND 1.1.0 actually does.

> **What each phase delivers, how it is demonstrated, and how lanes hand off.**
> Dates: [timeline.md](timeline.md) (estimates). Per-member commit-sized tasks: each
> member's `phase-plan.md` in [members/](../members/README.md).

---

## 1. Phase overview

| Phase | Dates (est.) | Goal | Gate demo |
|---|---|---|---|
| **0 · Foundations** | 26 Oct – 8 Nov 2026 | Repo, CI, typed IPC skeleton, supervised sidecar, first migration, hello-world installer | Install the CI-built installer on a clean Windows user; app starts, sidecar `/health` shows `db: ok, migrations: head` |
| **1 · Core loop** | 9 Nov – 13 Dec 2026 | Logger, History, PRs, rings, muscle map, XP/quests; food search; ML data collection | Log a real workout → PR toast → XP → map colours change; search "sambar 1 katori" and log it |
| **2 · Local AI** | 14 Dec 2026 – 17 Jan 2027 | Job queue, model manager, coach, meal scan, weekly review; classifier v0 | Scan a dosa plate → top-3 chips → correct one → logged; ask ARC about knee pain → injury protocol; switch AI off → everything still works |
| **3 · Ship v1.0** | 18 Jan – 7 Feb 2027 | Release pipeline, auto-update, backups, diagnostics, import, polish | Tag `v1.0.0` → release appears → an older install auto-updates; restore a backup; import a Strong CSV |
| **4 · Breadth (v1.1)** | 8 Feb – 21 Mar 2027 | Martial arts, flexibility, meditation, gallery, photos, trials, challenges, readiness, adaptive TDEE | All 11 sections usable; E2E + visual regression green in CI |
| **5 · MLOps loop (v1.2)** | 22 Mar – 16 May 2027 | Corrections → retraining → model-only update; drift report; shadow mode | A new classifier version passes the gate and reaches the app as a model-only update |

## 2. Gate checklist (every phase)

- [ ] Gate demo above runs live from a **CI-built installer**, not a dev server
- [ ] All tracker items for the phase are ✅ or explicitly moved (decision-log row)
- [ ] CI green on `main`; no skipped tests without an issue
- [ ] Contracts frozen for the phase are unchanged or changed additively
- [ ] Each member's work log is updated; each member demoed their own work
- [ ] Docs updated (index, architecture, ADRs for any new decision)
- [ ] Estimates replaced by measurements where the phase produced them

## 3. Per-phase deliverables by lane

| Phase | Dhanush (frontend) | Jegatheesan (backend) | Gokul (DevOps) | Navin (lead) |
|---|---|---|---|---|
| 0 | Secure Electron shell, typed preload, sidecar supervisor, design tokens | FastAPI skeleton, `/health`, SQLite WAL + Alembic baseline, OpenAPI stubs | Monorepo tooling, pre-commit, CI matrix, PyInstaller + NSIS hello-world | Docs, ADRs, contracts review, kickoff, repo rules |
| 1 | Logger UI, rings, muscle map component, History, onboarding | Workouts, PRs, event bus + outbox, muscle-load projector, XP/quests, food import | Coverage gate, contract-drift job, migration upgrade tests, link check | Formula specs + worked examples, DVC + MLflow Compose, photo collection, baseline classifier |
| 2 | Coach chat UI (SSE), scan UI with chips, proposal diffs, job progress | Job queue, model manager, Ollama client + fallbacks, coach rules, scan pipeline, weekly review | Dev Prometheus/Grafana, ML training image, cache + speed work on CI | Classifier v0, ONNX export + parity, eval gate, model benchmarks with J |
| 3 | States pass, backup/restore UI, diagnostics page, settings | Backup/restore, export, Strong/Hevy adapters, diagnostics bundle | Release workflow, auto-update channels, SBOM + checksums, packaged smoke test | Release notes, go/no-go, rollback drill, v1.0 evaluation report |
| 4 | New sections UI, gallery, photos compare, check-in, light theme | Section engines, trials/challenges, readiness, adaptive TDEE, encryption | E2E + visual regression in CI, optional kind + Helm lab for MLflow | Tamil test + decision, model manifest v2, evaluation update |
| 5 | Model health page, correction export UI | Prediction logging, shadow-mode switch | Model-only release workflow | Corrections → DVC v2, drift report, retrain + promote, shadow eval |

## 4. Non-blocking work and handoffs

- **Frontend never waits for backend:** it runs against a mock server generated from
  `docs/contracts/*.yaml` (Prism on `127.0.0.1:4010`, see [contracts/README.md](../contracts/README.md)).
- **Backend never waits for ML:** the scan pipeline ships with a `StubClassifier` that
  returns the VLM's own label at confidence 0.5 until classifier v0 lands.
- **ML never waits for the app:** training and evaluation run in `ml/` against DVC
  datasets; the only integration surface is `classifier.onnx` + `labels.json` + the
  preprocessing contract.
- **Everyone builds the installer from week two** so packaging problems surface early.

## 5. Contract freezes

| Contract | Frozen at end of | After freeze |
|---|---|---|
| IPC channels v1 | Phase 0 | additive only |
| `system`, `workouts`, `gamification`, `progress` | Phase 1 week 1 | additive only |
| `nutrition`, `coach` | Phase 2 week 1 | additive only |
| `import-export`, `.ascendbak` manifest | Phase 3 week 1 | additive only |

## 6. Cut order

If the team falls behind, cut in this order and log it:

1. Optional kind/Helm lab → 2. dev Grafana dashboards → 3. beta update channel →
4. VLM second opinion (scan stays classifier + tapped items) → 5. drill-down extras
(recovery curve) → 6. Tamil beta (ship English only) → 7. classifier coverage (fewer
classes; search covers the rest) → 8. trials.

**Never cut:** the release pipeline, backups before migrations, AI-off mode, red-flag triage,
the number-fidelity check on model replies ([ADR-0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md)).
