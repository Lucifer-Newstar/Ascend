# ASCEND — Documentation

> **The navigation hub for all ASCEND project documentation.**
> ASCEND is an offline Windows desktop fitness RPG with an on-device AI coach:
> workouts become quests, effort becomes XP, and every number comes from a
> deterministic engine the team can explain.
>
> Maintainer: Navin Jairam M (Team Lead, DevOps/MLOps). Updated whenever the
> structure changes (rule 2: the docs folder stays clean).
>
> Status: **1.2.0 in testing** on the `v12-test` branch (2026-10-23); the latest release is 1.1.0. The planning docs were written on 2026-10-20,
> before the first line of code, and are kept as the design record: where the built app
> differs from a plan, the [README](../README.md), the [CHANGELOG](../CHANGELOG.md) and the
> per-folder READMEs describe what shipped. Every date in the planning docs is an
> **estimate** unless it says otherwise.

---

## 1. Document Tree

```text
docs/
├── README.md                      ← you are here (index & reading order)
├── RULES_AND_BASELINE.md          ← design rules, checked rules and baseline numbers (v1.3)
│
├── project/                       ← WHAT & WHY
│   ├── proposal.md                ← the project proposal (incl. AI-assistance disclosure)
│   └── roadmap.md                 ← milestone-level roadmap (v0.1 → v1.0 → v1.2)
│
├── planning/                      ← HOW WE DECIDE
│   ├── README.md                  ← planning index + decision log
│   ├── product-vision.md          ← how the finished app looks & behaves
│   ├── features.md                ← locked scope: MVP v1.0 vs v1.1 vs later
│   ├── phases.md                  ← phases 0–5: deliverables, gates, handoffs
│   ├── timeline.md                ← calendar Oct 2026 → May 2027 (estimates)
│   ├── kickoff.md                 ← team kickoff: agenda, first issues, gate
│   ├── tracker.md                 ← status board through v1.0
│   └── integration-edge-cases.md  ← cross-member risk register
│
├── team/                          ← WHO & HOW WE WORK
│   ├── team-structure.md          ← roles, ownership matrix, reviewers
│   └── working-rules.md           ← project rules, commits, branches, DoD
│
├── members/                       ← PER-MEMBER PLANS (each member's folder)
│   ├── README.md                  ← member index + cross-member handoffs
│   ├── dhanush-frontend/          ← Member 1 — Electron / React UI / muscle map (+ work-log)
│   ├── jegatheesan-backend/       ← Member 2 — FastAPI sidecar / engines / Ollama (+ work-log)
│   ├── gokul-devops/              ← Member 3 — CI/CD / Docker / installers (+ work-log)
│   └── navin-lead/                ← Member 4 — lead / MLOps / classifier / releases (+ kickoff, study path)
│
├── ai/                            ← THE AI PART (coach, food recognition, models, MLOps)
│   ├── README.md                  ← principle, AI-off behaviour, feature → model → module map
│   ├── coach-llm.md               ← context, prompts, validation, safety, streaming, fallback
│   ├── prompt-library.md          ← every prompt, versioned, with schemas
│   ├── multilingual-tamil.md      ← Tamil / Tanglish beta: pipelines, test plan, go/no-go
│   ├── food-recognition.md        ← classifier, portions, VLM second opinion, corrections
│   ├── model-manager.md           ← VRAM budget, lifecycle state machine, downloads
│   ├── adaptive-planning-ai.md    ← rules vs AI in planning, proposals, weekly review
│   ├── data-and-privacy-for-ai.md ← what each model sees, consent, deletion
│   ├── evaluation.md              ← measured evaluation of the engines on synthetic users
│   ├── evaluation-ai.md           ← AI metrics, test sets, eval harness, CI gates (plan)
│   ├── mlops-lifecycle.md         ← DVC → MLflow → ONNX → registry → release walkthrough
│   ├── ai-risks.md                ← AI risk register
│   └── ai-roadmap.md              ← AI tasks per phase and member
│
├── architecture/                  ← SYSTEM DESIGN
│   ├── system-architecture.md     ← processes, modules, event bus, jobs, model manager
│   ├── awakening.md               ← the five-step first run (v5)
│   ├── hunter-stats.md            ← the five stats on Today (stats-v1)
│   ├── skill-trees.md             ← calisthenics skill trees and their criteria
│   ├── data-model.md              ← SQLite schema, migrations, derived data
│   ├── ml-pipeline.md             ← DVC → training → MLflow → ONNX → eval gate
│   ├── telemetry-model.md         ← local-only logs, events, metrics, crash reports
│   ├── security-privacy.md        ← threat model, Electron hardening, DPDP notes
│   ├── port-register.md           ← localhost ports + IPC channel register
│   ├── uml/                       ← 14-diagram UML set (Mermaid, PlantUML where needed)
│   └── adr/                       ← Architecture Decision Records 0001–0022 + template
│
├── contracts/                     ← API CONTRACTS (contracts-first)
│   ├── README.md                  ← conventions, mock server, drift check
│   ├── manifest.json              ← module → contract → router prefix
│   ├── ipc-contract.md            ← Electron preload ↔ main channels
│   ├── system.yaml                ← health, jobs, models, event stream
│   ├── workouts.yaml
│   ├── nutrition.yaml
│   ├── gamification.yaml
│   ├── coach.yaml
│   ├── progress.yaml
│   ├── intelligence.yaml          ← recovery, progression, TDEE, insights, programs
│   ├── skills.yaml
│   └── import-export.yaml
│
├── development/                   ← HOW TO BUILD
│   ├── contributing.md            ← branching, commits, PR rules, review
│   ├── branch-protection.md       ← main's protection rules and the PR flow
│   ├── local-setup.md             ← Windows 11 machine setup, step by step
│   ├── tech-stack.md              ← the stack at 1.0.0 & rationale
│   ├── design-system.md           ← colours, type, components (v5 "System" palette)
│   ├── motion.md                  ← motion rules, Reduce motion
│   └── accessibility.md           ← WCAG 2.2 AA checklist
│
├── operations/                    ← HOW TO SHIP & MEASURE
│   ├── evaluation.md              ← metrics, targets, how we measure
│   ├── loophole-sweep.md          ← XP loophole and bug sweep (v4)
│   └── release-process.md         ← versioning, release workflow, rollback
│
├── releases/                      ← user-facing release notes per version (v0.3.0, v1.0.0)
├── research/                      ← v8 research: anatomy, muscle mapping, engagement, trainer
└── screenshots/                   ← app screenshots used by the README
```

## 1a. Design-only documents

These describe plans, not the shipped app, and each one opens with a "Design record" note:
`project/proposal.md`, `project/roadmap.md`, everything in `planning/`, and each member's
`members/*/phase-plan.md`. The UML diagrams in `architecture/uml/` and the research notes in
`research/` are design material too. For what the app does today, read the
[README](../README.md), the [CHANGELOG](../CHANGELOG.md), `architecture/` and `contracts/`.

## 2. Index by Topic

| Topic | Go to |
|---|---|
| What is ASCEND and why build it? | [project/proposal.md](project/proposal.md) |
| What exactly are we building (MVP vs later)? | [planning/features.md](planning/features.md) |
| What does the finished app look and feel like? | [planning/product-vision.md](planning/product-vision.md) |
| Phases, gates and handoffs | [planning/phases.md](planning/phases.md) |
| The calendar | [planning/timeline.md](planning/timeline.md) |
| The first team meeting | [planning/kickoff.md](planning/kickoff.md) |
| What is done / in progress | [planning/tracker.md](planning/tracker.md) |
| Who owns what | [team/team-structure.md](team/team-structure.md) |
| Rules, commits, branches | [team/working-rules.md](team/working-rules.md) |
| My phase plan | [members/](members/README.md) — your folder |
| How the app is built (processes, modules) | [architecture/system-architecture.md](architecture/system-architecture.md) |
| Database tables and migrations | [architecture/data-model.md](architecture/data-model.md) |
| Food classifier + MLOps | [architecture/ml-pipeline.md](architecture/ml-pipeline.md) · walkthrough: [ai/mlops-lifecycle.md](ai/mlops-lifecycle.md) |
| **The AI part: what it does, which model, where the code is** | [ai/README.md](ai/README.md) |
| Coach prompts, validation and safety | [ai/coach-llm.md](ai/coach-llm.md) · [ai/prompt-library.md](ai/prompt-library.md) |
| Tamil / Tanglish (beta) | [ai/multilingual-tamil.md](ai/multilingual-tamil.md) |
| Meal photo recognition | [ai/food-recognition.md](ai/food-recognition.md) |
| Local models, VRAM, downloads | [ai/model-manager.md](ai/model-manager.md) |
| AI evaluation, risks and roadmap | [ai/evaluation-ai.md](ai/evaluation-ai.md) · [ai/ai-risks.md](ai/ai-risks.md) · [ai/ai-roadmap.md](ai/ai-roadmap.md) |
| Logs, events, crash reports (local only) | [architecture/telemetry-model.md](architecture/telemetry-model.md) |
| Security and privacy | [architecture/security-privacy.md](architecture/security-privacy.md) |
| Ports and IPC channels | [architecture/port-register.md](architecture/port-register.md) |
| UML diagrams | [architecture/uml/](architecture/uml/README.md) |
| Why we decided X | [architecture/adr/](architecture/adr/adr-template.md) · [planning/README.md §2](planning/README.md#2-decision-log) |
| API contracts (OpenAPI + IPC) | [contracts/](contracts/README.md) |
| Why this stack | [development/tech-stack.md](development/tech-stack.md) |
| How to contribute | [development/contributing.md](development/contributing.md) |
| Set up my Windows machine | [development/local-setup.md](development/local-setup.md) |
| How we measure success | [operations/evaluation.md](operations/evaluation.md) |
| How we ship a release | [operations/release-process.md](operations/release-process.md) |
| What changed in each version | [CHANGELOG](../CHANGELOG.md) · release notes in [releases/](releases/v1.2.0.md) |
| How accurate the engines are (synthetic users) | [ai/evaluation.md](ai/evaluation.md) |
| Design system, motion, accessibility | [development/design-system.md](development/design-system.md) · [motion.md](development/motion.md) · [accessibility.md](development/accessibility.md) |
| Research behind v8 | [research/](research/v8-gamified-engagement.md) |

### ADR list

| ADR | Decision |
|---|---|
| [0001](architecture/adr/0001-electron-react-desktop.md) | Electron + React + TypeScript desktop shell |
| [0002](architecture/adr/0002-fastapi-python-sidecar.md) | Python FastAPI sidecar for domain logic and AI |
| [0003](architecture/adr/0003-sqlite-local-only.md) | SQLite (WAL, Alembic) as the only database |
| [0004](architecture/adr/0004-ollama-qwen3-local-llm.md) | Ollama with qwen3:4b (coach) and qwen3-vl:2b (meals) |
| [0005](architecture/adr/0005-deterministic-engines-llm-explains.md) | Deterministic engines decide; the LLM only explains |
| [0006](architecture/adr/0006-own-food-classifier-indb-ifct.md) | Own Indian-food classifier + INDB/IFCT nutrient DB |
| [0007](architecture/adr/0007-modular-monolith-event-bus.md) | Modular monolith with an in-process event bus |
| [0008](architecture/adr/0008-electron-builder-pyinstaller-packaging.md) | electron-builder (NSIS) + PyInstaller packaging |
| [0009](architecture/adr/0009-offline-first-no-cloud.md) | Offline-first, no cloud, no accounts |
| [0010](architecture/adr/0010-import-export-formats.md) | Import/export formats (Strong/Hevy CSV, JSON, .ascendbak) |
| [0011](architecture/adr/0011-prompt-contracts-and-output-validation.md) | Prompts as versioned contracts; every model output validated |
| [0012](architecture/adr/0012-classifier-first-meal-scan.md) | Classifier-first meal scan; VLM as an optional second opinion |
| [0013](architecture/adr/0013-custom-exercises.md) | Custom exercises: rules first, local model second, online research only with consent |
| [0014](architecture/adr/0014-recovery-engine-v2.md) | Recovery engine v2: per-muscle readiness from dose, decay and personal factors |
| [0015](architecture/adr/0015-progression-engine-prog-v1.md) | Progression engine prog-v1: double progression with RPE autoregulation and stall detection |
| [0016](architecture/adr/0016-explanations-and-system-voice.md) | Explanations from templates, optional model phrasing behind the coach guard, and three System notices |
| [0017](architecture/adr/0017-evaluation-synthetic-users.md) | Evaluating the engines on seeded synthetic users |
| [0018](architecture/adr/0018-adaptive-tdee-kalman.md) | Adaptive TDEE with a Kalman filter (tdee-v1) |
| [0019](architecture/adr/0019-weekly-diet-insights.md) | Rule-based weekly diet insights (insights-v1) |
| [0020](architecture/adr/0020-workout-programs.md) | Workout programs read from the log (programs-v1) |
| [0021](architecture/adr/0021-detailed-muscle-taxonomy.md) | Detailed muscle taxonomy (muscles-v2) and rule-based mapping (muscle-map-v1) |
| [0022](architecture/adr/0022-weekly-boss-raid.md) | Weekly boss raid (boss-v1) |

## 3. Reading Order for a New Member

1. **Start here** — get the map.
2. **[team/](team/team-structure.md)** — who we are and how we work (rules first).
3. **[planning/features.md](planning/features.md)** — what we are building. Scope is locked; read it before writing code.
4. **[planning/phases.md](planning/phases.md) + [timeline.md](planning/timeline.md)** — when things happen and what "done" means per phase.
5. **[members/<your-folder>/](members/README.md)** — your role, your commit-sized tasks.
6. **[architecture/system-architecture.md](architecture/system-architecture.md)** and the ADRs — read before touching any interface.
   Working on anything AI? Then **[ai/README.md](ai/README.md)** next.
7. **[contracts/](contracts/README.md)** — the API you build against or implement.
8. **[development/local-setup.md](development/local-setup.md)** — set up your machine, then open your first PR.
9. **[operations/](operations/evaluation.md)** — how the project will be judged.

## 4. Housekeeping Rules (rule 2 in practice)

- **One purpose per file.** Every document answers one question; a new topic gets a new file in the right folder.
- **No orphans.** Every file is reachable from this index; when you add a file, add its row to §2.
- **Living documents.** Planning docs change; changes go in the decision log ([planning/README.md §2](planning/README.md#2-decision-log)), never silently.
- **ADRs for architecture.** Any change to the stack, a process boundary or a contract needs an ADR (copy [adr-template.md](architecture/adr/adr-template.md)).
- **Links stay green.** CI checks every relative link in the repo's Markdown files (`scripts/check_md_links.py`, job "docs"; see [contributing.md](development/contributing.md#5-ci-checks-on-every-pr)). Run it locally with `python scripts/check_md_links.py`.

## 5. Honesty Rules for These Docs

- **Estimates are labelled.** Dates, hours, accuracies, latencies and model speeds are estimates until measured; measured values replace them with a date and a link to the run.
- **Unverified is labelled.** Anything not yet tested on our hardware (Tamil quality of qwen3:4b, VLM box quality on Indian plates, signing options) is marked *unverified*.
- **AI assistance is disclosed.** Parts of the code were written with AI assistance ([proposal §9](project/proposal.md#9-ai-assistance-disclosure)). Whoever opens a PR must be able to explain every line of it.
- **Original IP only.** ASCEND is inspired by the *genre* of workout RPGs. No names, art, logos, characters or terminology from any existing anime, manhwa or game are used.
- **No personal contact data** (phone numbers, home addresses) in the repo.
