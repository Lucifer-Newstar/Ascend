# ASCEND — Project Proposal

> **An offline Windows desktop fitness RPG with an on-device AI coach.**
> Team project led by Navin Jairam M. Proposal date: 2026-10-20.
> Source of truth for features and numbers: *ASCEND Product + Engineering Plan v2*
> (20 Oct 2026, 64 pages), kept outside the repo; this proposal summarises it.

---

## 1. Problem

Most fitness apps split the job in three: a logger (Strong, Hevy), a nutrition tracker
(MyFitnessPal, HealthifyMe) and a motivation layer (streaks, rings, games). They are
cloud-first, often paywall basic features, and handle Indian home food poorly. Gamified
workout apps motivate well but rarely explain *why* a number changed, and their "AI" is
usually a black box that can give unsafe advice.

## 2. Proposed Solution

ASCEND is a Windows desktop app that runs **fully offline**:

- **One logger** behind Gym, Calisthenics, Cardio, Martial Arts, Flexibility and Meditation.
- **A game layer** (XP, levels, stat points, daily quests, streaks with freezes, letter
  ranks E → S, weekly challenges) that rewards consistency, never injury.
- **An anatomical muscle map** coloured by weekly effective sets and recovery, with a
  1-day → 1-month drill-down.
- **Diet that understands Indian food** — INDB/IFCT nutrient data, katori/ladle/piece
  portions, oil level, and a meal-photo scan with top-3 guesses and one-tap correction.
- **ARC, an on-device coach** (qwen3:4b via Ollama) that explains plans, handles injury
  conversations and writes the weekly review — while **deterministic engines make every
  decision**, so the app works fully with AI switched off.

## 3. Objectives

| # | Objective | Measured by ([evaluation.md](../operations/evaluation.md)) |
|---|---|---|
| O1 | Ship an installable, auto-updating v1.0 by ~7 Feb 2027 (estimate) | Tagged release with installer, checksums, SBOM |
| O2 | Every number is reproducible from versioned formulas | Golden-file tests per `algo_version` |
| O3 | Indian meal recognition that is useful in practice | Top-3 accuracy, calorie MAE, correction rate |
| O4 | A coach that is fast enough on a 4 GB laptop GPU | First-token latency, tokens/s (benchmarked) |
| O5 | No data leaves the PC | Network-egress test in CI; no telemetry code paths |
| O6 | Every member ends with a real, explainable commit history | Per-member commits/PRs mapped to their phase plan |

## 4. Scope

**In scope (v1.0 MVP):** see [features.md](../planning/features.md) §1. In short: Gym,
Calisthenics and Cardio logging; rings; muscle map + drill-down; XP/quests/streaks/ranks
E → C; Indian food search + photo scan; coach plans, injury protocol, weekly review,
English chat (Tamil beta); AI-off mode; backup/export; auto-update.

**Out of scope:** cloud sync, accounts, online leaderboards/guilds, a mobile app, live
wearable sync, AI judging of body photos, medical diagnosis.

## 5. Architecture in One Paragraph

Electron (React + TypeScript, Tailwind, shadcn/ui) talks through a typed preload bridge
to the main process, which supervises a **Python 3.12 FastAPI sidecar** on a random
localhost port with a launch token. The sidecar is a modular monolith (workouts,
nutrition, gamification, coach, progress, ai) with a transactional-outbox event bus and
a SQLite job queue, storing everything in **SQLite (WAL, Alembic)** plus local files.
A model manager drives **Ollama** (qwen3:4b coach, qwen3-vl:2b as an optional meal second opinion, one GPU
model at a time) and **ONNX Runtime** (our Indian-food classifier, on CPU). Details:
[system-architecture.md](../architecture/system-architecture.md); the AI part in full:
[docs/ai/](../ai/README.md).

## 6. Team

ASCEND is built by the same four-member team as AegisDeploy.

| # | Member | Role | Folder |
|---|---|---|---|
| 1 | Dhanush Kumar S | Frontend: Electron, React UI, design system, muscle map | [dhanush-frontend](../members/dhanush-frontend/README.md) |
| 2 | Jegatheesan K | Backend: FastAPI sidecar, engines, SQLite, Ollama integration | [jegatheesan-backend](../members/jegatheesan-backend/README.md) |
| 3 | Gokul J | DevOps: CI/CD, Docker, installers, release automation | [gokul-devops](../members/gokul-devops/README.md) |
| 4 | Navin Jairam M | Team Lead: architecture, MLOps pipeline, food classifier, releases | [navin-lead](../members/navin-lead/README.md) |

Full ownership matrix: [team-structure.md](../team/team-structure.md).

## 7. Methodology

- **Contracts first.** OpenAPI per module and an IPC contract are agreed before code
  ([contracts/](../contracts/README.md)), so frontend and backend build in parallel
  against a mock server.
- **Phased delivery with gates** ([phases.md](../planning/phases.md)): each phase ends
  with a demo and a checklist, not a date alone.
- **Small commits, real history.** Each member's phase plan lists commit-sized tasks
  (1–3 hours each). Commits are dated when they actually happen — no backdating.
- **Decisions recorded** as ADRs ([adr/](../architecture/adr/adr-template.md)).

## 8. Prior Work

- **Gamified-Fitness-Tracker** (Navin, June 2026, public repo): a browser "FitQuest"
  prototype — HTML/Bootstrap pages, Supabase sign-up/login, a GitHub Actions workflow
  with HTML/JS lint stages and a Netlify preview deploy. Reusable for ASCEND: the
  feature idea list (XP, levels, streaks, badges) and the CI lesson that lint steps
  ending in `|| true` / `|| echo` never fail a build. Not reused: the code (web +
  cloud auth do not fit an offline desktop app).
- **AegisDeploy** (team project): this docs structure, the ADR habit, contracts-first
  workflow and per-member folders are modelled on its `docs/`.

## 9. AI-Assistance Disclosure

Parts of the code were written with AI assistance. The member who commits any change
owns it: they test it and can explain it in review.

## 10. Risks (top 5)

| Risk | Mitigation |
|---|---|
| Scope creep | Frozen MVP table; new ideas go to `BACKLOG.md` |
| Local AI too slow on 4 GB VRAM | Model tiers, rules-only mode, AI fully optional |
| Unsafe advice | Rules decide; red-flag words bypass the model; plan changes need user approval |
| Packaging pain (Python + Electron on Windows) | Installer built from Phase 0 week 2 |
| Uneven availability (all four are final-year students) | Contracts + mocks so nobody blocks; cut list in [phases.md](../planning/phases.md#6-cut-order) |

Full register: [integration-edge-cases.md](../planning/integration-edge-cases.md).

## 11. Naming and IP

"ASCEND" and "ARC" are working names; check trademarks before any public release. The
app uses original names, art and terms only — generic mechanics (XP, levels, letter
ranks) are fine; names, logos, characters or signature terminology from existing
anime, manhwa or games are not. The muscle-map artwork is MIT-licensed
(react-muscle-highlighter 1.2.0); its notice ships in the About page.

## 12. Not Medical Advice

ASCEND is not a medical device. It says so at onboarding and in every injury protocol.
