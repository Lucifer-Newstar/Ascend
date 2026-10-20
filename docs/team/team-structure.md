# Team Structure

> ASCEND is a **four-member team project** (the AegisDeploy team). This document
> defines each member's role, responsibilities and repository ownership, so everyone
> knows their lane and where the lanes meet.
>
> Maintainer: Member 4 (Team Lead). Updated whenever responsibilities shift.

---

## 1. Members and Roles

> Each member has a planning folder in [docs/members/](../members/README.md) with
> their role, commit-sized phase plan and work log.

| # | Member | Role | Primary responsibilities |
|---|--------|------|--------------------------|
| 1 | **Dhanush Kumar S** | Frontend Developer | Electron main/preload/renderer, React UI, design system (Tailwind + shadcn/ui), dashboard rings, anatomical muscle map + drill-down, logger UI, coach chat UI, onboarding, states, notifications |
| 2 | **Jegatheesan K** | Backend Developer | FastAPI sidecar, SQLite + Alembic, event bus + outbox, job queue, deterministic engines (load, progression, PRs, XP, quests, TDEE, ETA), coach rules, **Ollama integration** (client, model manager runtime, fallbacks), import/export adapters, OpenAPI implementation |
| 3 | **Gokul J** | DevOps Engineer | GitHub Actions CI/CD, pre-commit, dev container + ML training image, PyInstaller sidecar build, electron-builder NSIS installer, auto-update + release automation, checksums/SBOM, packaged-app smoke tests, dev-time Prometheus/Grafana |
| 4 | **Navin Jairam M** | **Team Lead** — architecture, MLOps, releases | See §2 |

---

## 2. Team Lead (Navin Jairam M — Member 4)

**Technical ownership**

- Architecture and ADRs (`docs/architecture/`), contracts review (`docs/contracts/`)
- **MLOps pipeline:** DVC datasets, MLflow tracking + registry (Docker Compose), the
  evaluation gate, model manifest, drift report, retraining from corrections
- **Indian-food classifier:** dataset curation and labelling, training (PyTorch + timm on
  the RTX 3050 via WSL2), ONNX export + parity test, preprocessing contract for the sidecar
- **Releases:** version numbers, release notes, go/no-go, beta → stable promotion,
  model-only releases, rollback decisions (Gokul automates; Navin decides)
- Local model benchmarking (tokens/s, VRAM) with Jegatheesan
- Evaluation protocol and reports ([evaluation.md](../operations/evaluation.md))

**Coordination**

- Runs the kickoff and weekly sync ([kickoff-guide.md](../members/navin-lead/kickoff-guide.md))
- Keeps the tracker, timeline and decision log current
- Reviews any change that touches a contract, a process boundary or the stack
- Unblocks: when two lanes disagree on an interface, the lead decides and logs it

**Personal learning goal:** DevOps → MLOps — Linux/Bash, Docker, GitHub Actions, then
AWS SAA later; this project carries the MLOps and release-engineering half
([study-path.md](../members/navin-lead/study-path.md)).

---

## 3. Repository Ownership

Ownership = primary author/maintainer. Reviewer = must approve before merge.

| Area | Owner | Reviewer |
|---|---|---|
| `apps/desktop/` (Electron main + preload in `electron/`, React renderer in `src/`) | Dhanush | Navin (IPC/security), Gokul (packaging paths) |
| `apps/desktop/electron/sidecar.ts` (supervisor) | Dhanush | Gokul + Jegatheesan |
| `services/sidecar/app/core/` (db, events, jobs, security) | Jegatheesan | Navin |
| `services/sidecar/app/modules/*` (domain engines) | Jegatheesan | Navin (formulas), Dhanush (API shape) |
| `services/sidecar/app/ai/` (Ollama client, model manager, ONNX runtime) | Jegatheesan | Navin |
| `ml/` (datasets, training, export, eval) | Navin | Jegatheesan (integration) |
| `.github/workflows/`, `build/`, `infra/` (docker, compose, grafana) | Gokul | Navin |
| electron-builder config, `services/sidecar/packaging/ascend-sidecar.spec` (PyInstaller) | Gokul | Dhanush, Jegatheesan |
| `docs/contracts/`, `packages/shared/` | Jegatheesan (OpenAPI), Dhanush (IPC types) | Navin |
| `docs/architecture/`, `docs/planning/`, `docs/team/` | Navin | All |
| `docs/members/<folder>/` | that member | — |
| Root files (`README.md`, `CHANGELOG.md`, configs) | Navin | All |

> **Shared areas:** test fixtures (`tests/fixtures/`) and the exercise/food seed data.
> Anyone may add; changes to existing fixtures need the owner of the code under test.

---

## 4. Coordination Model

1. **Branches & PRs.** Each member works on `feat/<member>-<area>-<topic>` and merges
   via PR; `main` stays releasable. See [working-rules.md §3](working-rules.md#3-branch-workflow).
2. **Architecture gate.** Any change to a process boundary, contract or the stack needs
   an ADR reviewed by the Team Lead.
3. **Contracts first.** Frontend builds against the OpenAPI mock server; backend
   implements to the same contract; CI fails on drift ([contracts/README.md](../contracts/README.md)).
4. **Weekly sync (30 min).** Each member: done / next / blocked; demo of the week; the
   lead updates [tracker.md](../planning/tracker.md).
5. **Async by default.** Questions go in the GitHub issue or PR, not only in chat, so the
   decision is findable later.

## 5. Interfaces Between Lanes

| From → To | What | When |
|---|---|---|
| Jegatheesan → Dhanush | OpenAPI contracts + mock server, SSE event names | Phase 0 |
| Dhanush → Jegatheesan | IPC contract, sidecar launch protocol (port, token, data dir) | Phase 0 |
| Gokul → all | CI pipeline, dev container, installer artefact | Phase 0 |
| Navin → Jegatheesan | Formula specs (load model, XP, TDEE…) with worked examples | Phase 1 |
| Navin → Jegatheesan | Classifier ONNX + `labels.json` + preprocessing contract | Phase 2 |
| Jegatheesan → Navin | Scan predictions + corrections export (for MLOps loop) | Phase 2 / 5 |
| Gokul → Navin | Release workflow, update channels, SBOM | Phase 3 |
| Navin → all | Release go/no-go, changelog | Every release |

## 6. If Someone Has to Step Back

Final-year schedules change. If a member is out for more than two weeks: their open
issues are re-labelled `needs-owner`, the lead re-plans the phase using the cut order
([phases.md §6](../planning/phases.md#6-cut-order)), and nobody inherits half-finished
branches without a handover note in the work log.
