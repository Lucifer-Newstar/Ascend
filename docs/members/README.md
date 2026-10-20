# Member Plans

Each member folder contains:

- **README.md — role and interfaces:** responsibility, owned repository areas, contracts provided or consumed.
- **phase-plan.md — delivery commitment:** that member's work per phase as **commit-sized tasks** (1–3 hours each, one Conventional Commit or a small PR), with dependencies and a completion check.
- **work-log.md — dated delivery notes:** what landed, when, and with which handoff (starts empty).

The lead's folder also has **kickoff-guide.md** (how to run the first meeting and the
weekly sync) and **study-path.md** (what to read and practise, in order).

Team-level ownership is in [team-structure.md](../team/team-structure.md). Shared scope is in
[features.md](../planning/features.md); phase gates are in [phases.md](../planning/phases.md).

---

## 1. Member index

| # | Member | Role | Folder | Main areas |
|---|---|---|---|---|
| 1 | **Dhanush Kumar S** | Frontend developer | [dhanush-frontend](dhanush-frontend/README.md) | Electron main/preload, React UI, design system, muscle map, chat + scan UI |
| 2 | **Jegatheesan K** | Backend developer | [jegatheesan-backend](jegatheesan-backend/README.md) | FastAPI sidecar, engines, SQLite/Alembic, event bus, jobs, Ollama integration, import/export |
| 3 | **Gokul J** | DevOps engineer | [gokul-devops](gokul-devops/README.md) | CI/CD, pre-commit, Docker images, PyInstaller + NSIS installer, auto-update, release automation |
| 4 | **Navin Jairam M** | Team lead · MLOps · releases | [navin-lead](navin-lead/README.md) | Architecture, contracts review, food classifier, DVC/MLflow/eval gate, releases, evaluation |

## 2. Main handoffs

```text
Jegatheesan: OpenAPI contracts + mock ─────────▶ Dhanush (Phase 0)
Dhanush: IPC contract + supervisor ────────────▶ Jegatheesan, Gokul (Phase 0)
Gokul: CI + dev container + installer ─────────▶ all (Phase 0)
Navin: formula specs + worked examples ────────▶ Jegatheesan (Phase 1)
Jegatheesan: dashboard/muscle APIs ────────────▶ Dhanush (Phase 1)
Navin: classifier.onnx + labels.json ──────────▶ Jegatheesan (Phase 2)
Jegatheesan: chat SSE + scan job API ──────────▶ Dhanush (Phase 2)
Gokul: release workflow + update channels ─────▶ Navin (Phase 3)
Jegatheesan: corrections export ───────────────▶ Navin (Phase 5)
All: demo of own work ─────────────────────────▶ phase gate review
```

While an implementation is pending, build against the contract mock
([contracts/README.md §3](../contracts/README.md#3-mock-server-frontend-development)).
Do not silently change an interface another member uses.

## 3. Commit-sized tasks: how to use them

- Each `- [ ]` line in a phase plan is roughly **one commit** (or one small PR) and already
  carries a suggested Conventional Commit subject. Turn it into a GitHub issue when you
  start; tick it when merged.
- Write the commit yourself, on the day you do the work. If a task turns out bigger,
  split it into several honest commits — never squash a week into one, never backdate.
- Tasks marked **(pair: X)** are done together; each person commits their own part.
- Rough count to v1.0 (estimate): Dhanush ~70, Jegatheesan ~80, Gokul ~60, Navin ~65
  commits — a genuine history for everyone.
- Some early tasks overlap with the v0.1 code skeleton that already exists. At the
  kickoff, the owner of each lane reviews that code, ticks the tasks it already covers
  (with a link to the commit), and takes ownership of explaining it. Nobody re-commits
  existing work under their own name.

## 4. Keeping plans current

1. Check the phase gate and feature acceptance criteria before starting a phase.
2. Keep your `phase-plan.md` ticked and honest; move undone items with a note.
3. Add a line to `work-log.md` for anything user-visible or cross-lane.
4. Tell the lead when role ownership or an interface changes; record it in the decision log.
