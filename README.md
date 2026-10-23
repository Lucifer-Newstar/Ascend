# ASCEND

[![CI](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/ci.yml)
[![ML](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/ml.yml/badge.svg?branch=main)](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/ml.yml)
[![Windows installer](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/release.yml/badge.svg)](https://github.com/Lucifer-Newstar/Ascend-/actions/workflows/release.yml)
[![Latest release](https://img.shields.io/github/v/release/Lucifer-Newstar/Ascend-?sort=semver)](https://github.com/Lucifer-Newstar/Ascend-/releases/latest)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

**An offline Windows desktop fitness RPG.** Log workouts and Indian meals, earn XP, clear daily
quests, keep a streak and rank up from **E to S**, while a muscle map shows which muscles are
under-trained, recovering or overreached. Everything runs and is stored on your own PC; an
optional local AI coach (Ollama + `qwen3:4b`) explains your numbers, and the app works fully
without it.

ASCEND is our final-year project: an Electron + React desktop app, a FastAPI + SQLite engine
that runs beside it, deterministic training and diet engines, and an MLOps pipeline.

![Today](docs/screenshots/ASCEND_v5_Today.png)

| Train: three-pane logger | Skills: tree canvas |
|---|---|
| ![Train](docs/screenshots/ASCEND_v5_Train.png) | ![Skills](docs/screenshots/ASCEND_v5_Skills.png) |

> Screens use demo data from `app.devtools.seed_demo`. The v0.1 MVP screens are kept in
> [docs/screenshots](docs/screenshots/).

**Contents:** [Download](#download-and-install) · [Features](#features) ·
[Limitations](#honest-limitations) · [Architecture](#architecture) · [Tech stack](#tech-stack) ·
[Developer quick start](#developer-quick-start) · [Testing and CI](#testing-and-ci) ·
[Docs](#documentation) · [Team](#team) · [Credits](#credits-and-licences)

## Download and install

1. Open the [latest release](https://github.com/Lucifer-Newstar/Ascend-/releases/latest) and download **`ASCEND-Setup-<version>.exe`**
   (for 1.0.0: `ASCEND-Setup-1.0.0.exe`). `SHA256SUMS.txt` next to it lets you check the download.
2. Run it. The installer is **not code-signed yet**, so Windows SmartScreen shows "Windows protected
   your PC": click **More info → Run anyway**.
3. Pick a folder (default: `%LOCALAPPDATA%\Programs\ASCEND`, no admin rights needed) and finish.
   ASCEND starts and walks you through the five-step first run.

**System requirements:** Windows 10 or 11, 64-bit (x64). Nothing else: the engine ships inside the
installer. For the optional AI coach, install [Ollama](https://ollama.com) and run
`ollama pull qwen3:4b` (about 2.5 GB; fits a 4 GB GPU, see [AI coach](#optional-ai-coach)).

**Your data** is one SQLite file in `%APPDATA%\ASCEND\data`. It stays on your PC, is kept when you
uninstall, and a reinstall picks it up again. The app also writes a daily automatic backup.

Check a download in PowerShell (compare with the line for the file in `SHA256SUMS.txt`):

```powershell
Get-FileHash .\ASCEND-Setup-1.0.0.exe -Algorithm SHA256
```

Release notes for each version: [GitHub Releases](https://github.com/Lucifer-Newstar/Ascend-/releases) and [docs/releases](docs/releases/);
the full history is in [CHANGELOG.md](CHANGELOG.md).

## Features

### Screens

| Screen | What it does |
|---|---|
| **Today ("Hunter HQ")** | The daily quest as a System window with time left, a status panel (STR, AGI, END, VIT, INT) where every number has a "Why?", up to three insights spoken by the trainer, Instructor Iskra Vey (switchable to a plain mode), the weekly boss raid ([ADR-0022](docs/architecture/adr/0022-weekly-boss-raid.md)), Quick log, check-in, fuel and the muscle map on a 12-column grid. |
| **Train** | Keyboard-first logger: last session's sets in grey next to today's, the next set pre-filled from last time (Enter logs it), a rest bar (Space pauses), muscles hit and the skills the exercise feeds. |
| **Skills** | A zoomable, pannable tree canvas per family; arrow keys move along the edges; a drawer shows the criteria, the estimate (only with enough data) and "Train this skill". |
| **Ctrl+K** | Command bar: `bench 80x5 @8`, `log 3x8 pull-up`, `plank 45s`, `weight 81.4`, `add 2 eggs`, `train front lever`, a page name, or any question for the Coach. Rule-based, no model. |
| **Awakening** | Five-step first run with an equipment checklist (respected by quests and skill suggestions) and a baseline test logged as a real session. |
| **Streaks** | Freezes cover missed days, and a missed day never removes XP, levels, ranks or skills; the next quest adds a short Comeback item instead. |
| **Accessibility and motion** | WCAG AA colours in both themes (unit-tested), labelled controls, axe-clean screens, Reduce motion honoured everywhere, optional sound off by default. |

Shortcuts: **Ctrl+K** command bar · **Ctrl+1…0** pages · **Enter** log the set shown ·
**Space** pause rest · arrows on the skill canvas.

### Training and recovery engines

Deterministic engines, pure Python on the CPU. The local model is optional and only ever phrases
what the engines computed.

| What | How it works |
|---|---|
| **Recovery (`recovery-v2`)** | Per-muscle readiness for all 54 muscles and heads (taxonomy v2, [ADR-0021](docs/architecture/adr/0021-detailed-muscle-taxonomy.md)) from each set's dose (muscle weight × effort from reps in reserve × volume; holds by seconds), decayed by the muscle's half-life × your personal factor, adjusted by today's check-in. Drives the muscle map, quests and the weekly review. [ADR-0014](docs/architecture/adr/0014-recovery-engine-v2.md) |
| **Personal recovery factors** | One factor per muscle group, fitted after every workout from how your performance follows fatigue. Starts at the population value, moves only with evidence, shown with a 90 % interval and as **"you vs population"** on the muscle drill-down. |
| **Progression (`prog-v1`)** | The logger's **suggestion card** (Use it / Keep mine / Why?): double progression in your rep zone, equipment-aware increments (never more than 10 % at once), RPE autoregulation, e1RM tracking, stall detection with a 10 % reset, hold progressions, and skill-tree criteria for calisthenics. No increase while the muscles are under 40 % recovered. [ADR-0015](docs/architecture/adr/0015-progression-engine-prog-v1.md) |
| **"Why?" everywhere** | Every target and readiness shows its formula and inputs. With AI on, `qwen3:4b` may phrase one sentence, shown only if every number passes the coach guard; otherwise the template sentence. [ADR-0016](docs/architecture/adr/0016-explanations-and-system-voice.md) |
| **The System speaks, rarely** | Three notices, each shown once: Deload advised, Target raised, Muscle recovered. |
| **Evaluation** | A seeded synthetic-user simulator with baselines, in [docs/ai/evaluation.md](docs/ai/evaluation.md) ([ADR-0017](docs/architecture/adr/0017-evaluation-synthetic-users.md)). On synthetic users, prog-v1 targets were hit within 1 rep on 93.1 % of exposures (linear +2.5 kg with resets: 71.8 %) and too hard on 2.7 % (22.4 %); recovery-v2 readiness correlates with the simulated truth at Pearson r 0.842-0.926 on the 54-muscle taxonomy (fixed 48 h rule: 0.552-0.579). |

### Diet engines and workout programs

| What | How it works |
|---|---|
| **Adaptive TDEE (`tdee-v1`)** | A two-state Kalman filter on trend weight and expenditure, fed by your weigh-ins and logged meals. It starts from Mifflin-St Jeor with a wide range and narrows as data comes in. Missing days widen the range instead of breaking it. The weekly calorie target moves only on Mondays, only after a week with 6 logged days and 4 weigh-ins, and by at most 150 kcal. Fuel shows the range, the target, completeness and the reason. [ADR-0018](docs/architecture/adr/0018-adaptive-tdee-kalman.md) |
| **Weekly insights (`insights-v1`)** | Six fixed rules over the last 7 complete days: intake vs target, protein, weekend vs weekday, weight trend vs goal, adaptive vs formula, and logging gaps. Progress shows up to three findings, each with a "Why?", plus the list of rules that were checked. [ADR-0019](docs/architecture/adr/0019-weekly-diet-insights.md) |
| **Workout programs (`programs-v1`)** | Four built-in programs: full body 3 days, upper/lower 4 days, push/pull/legs 6 days, and home full body 3 days. The Program card on Train shows the next session with each exercise's target from your progression and the sets you have done today. The plan reads your log: a finished workout that covers half of a program day counts as that day, so a missed day shifts the plan instead of skipping a session. [ADR-0020](docs/architecture/adr/0020-workout-programs.md) |
| **Evaluation** | Synthetic users, seed 2026 ([docs/ai/evaluation.md §5](docs/ai/evaluation.md)). Median TDEE error at day 56 is 82.8 kcal (formula: 194.7), and the 14-day weight prediction from day 56 is 50.3 % more accurate than the formula's. The intake, protein and weekend insights have precision 0.935-1.0. tdee-v1 takes 3.08 ms on a one-year history. |

### Game layer, trainer and safety nets

| What | How it works |
|---|---|
| **XP, ranks, quests, streaks** | XP per set and session on a `100 × L^1.3` level curve, ranks E→S, a rule-generated daily quest, streak freezes; every formula is versioned. A missed day never removes XP, levels, ranks or skills. |
| **Weekly boss raid (`boss-v1`)** | Each Monday a boss with HP sized to a week of your training; every set deals 1 damage. Beat it by Sunday for +150 XP and a title on your Hunter profile; if it survives, nothing is lost. [ADR-0022](docs/architecture/adr/0022-weekly-boss-raid.md) |
| **Instructor Iskra Vey** | An original trainer character who speaks your insights on Today, with four expressions. She only wraps the engine's own sentence, so the numbers never change. A switch turns her into the plain System style. |
| **Detailed muscle map** | 54 muscles and heads, front, back and a deep layer, in ASCEND's own artwork. Every exercise is mapped to heads by `muscle-map-v1`. [ADR-0021](docs/architecture/adr/0021-detailed-muscle-taxonomy.md) |
| **Quick log and honest numbers** | Log a set, meal or weigh-in from Today; "rough · based on N" badges on numbers with too little data; Settings → Today's numbers lists the engine, version and data behind every number. |
| **Backups, import and export** | One automatic `.ascendbak` snapshot per day (newest 14 kept), backups before updates and restores, restore with a database check; export to JSON or CSV and re-import. |
| **Exercise library** | 873 free-exercise-db exercises plus calisthenics progressions and timed holds, each with a photo or a designed tile; add your own exercise with rules, the local AI or an optional online lookup (wger.de, Wikipedia), each field with its source. |
| **Indian food log** | Approximate Indian foods (idli, dosa, sambar, chapati, dal, curd...) with katori and piece portions, daily totals and the adaptive calorie target. Food is logged by search; photo recognition is not in the app (see [ml/](ml/README.md)). |

### What was in the MVP (v0.1.0)

| Feature | Where |
|---|---|
| Onboarding: age, sex, height, weight, goal, activity → BMR/TDEE (Mifflin-St Jeor), shown as an **estimate** | `progress`, `nutrition/tdee.py` |
| Workout logger: 41 seeded exercises with primary/secondary muscle weights, sets with kg / reps / RPE, **PR detection** (Epley e1RM), rest timer | `workouts` |
| Gamification: XP per set and session, level curve `100 × L^1.3`, ranks E→S, rule-generated **daily quest**, streak with **freezes**; all formulas versioned | `gamification` |
| Muscle recovery: per-muscle effective sets with recovery decay → under / optimal / recovering / over (replaced by recovery-v2 in v6) | `progress/muscle_load.py` |
| Today (was Dashboard): three rings (quest tasks, kcal eaten, kcal burned), today's quest, XP bar, front/back muscle map with a deep layer | `apps/desktop/src/pages/Dashboard.tsx` |
| Diet log: 31 approximate Indian foods (idli, dosa, sambar, chutneys, rice, chapati, dal, curd...) with katori/piece portions, daily totals | `nutrition` |
| Coach: rule-based tips always; local Ollama `qwen3:4b` if running; **AI on/off toggle** | `coach` |
| History by day (workouts + meals) and export to **JSON / CSV** | `progress/history.py` |
| **Calisthenics skill trees** (12 trees, unlock criteria from logged sets, estimates only with enough data) | `skills`, `pages/Skills.tsx` |
| **Exercise gallery**: 873 free-exercise-db exercises + calisthenics progressions, timed holds, search and filters; every card has a photo or a designed tile | `workouts/library.py`, `pages/Library.tsx` |
| **Add your own exercise**: rules → local AI → optional online research (wger.de, Wikipedia), every field with its source and confidence, a research report to confirm, a local lookup log | `workouts/custom.py`, ADR-0013 |

## Honest limitations

- **Evaluated on simulated users, not real people.** Every accuracy figure above comes from a seeded
  synthetic-user simulator ([docs/ai/evaluation.md](docs/ai/evaluation.md)). No real-user study
  exists yet. programs-v1's "half of a day's exercises" matching has not been checked against
  real training logs.
- **Recovery r ≈ 0.9 is partly circular.** It is measured against the simulator's own ground truth,
  which uses the same model family as the engine. It shows the estimation works under those
  assumptions, not that people recover this way.
- **Stall detection is weak:** precision 0.113, recall 0.62 on synthetic stalls. That is why a stall
  alone never triggers a deload.
- **The adaptive TDEE is slow to learn.** Only 57% of synthetic users are within 150 kcal of their
  true expenditure on day 28; the target stays on the formula until the estimate settles. If meals
  are under-logged, "you burn" matches what was logged.
- **The weight-trend insight is a hint:** precision 0.397, recall 0.408 on synthetic weeks.
- **Programs are a fixed catalog.** You cannot edit them or build your own yet.
- **The food classifier is not in the app.** The ML pipeline in [ml/](ml/README.md) runs end to end,
  but only on synthetic smoke data (generated shapes, not food photos); its metrics say nothing
  about real food recognition.
- **The local-model path is tested with a mocked Ollama.** Real `qwen3:4b` phrasing is not covered
  by tests; anything it writes is shown only if the coach's number guard passes. Without a model the
  app shows template text and is fully functional.
- **Unsigned installer.** SmartScreen warns until the project has a code-signing certificate.
- Food values are approximate home-style figures, and BMR, e1RM and calorie burn are standard
  estimation formulas. ASCEND is not medical or dietary advice.
- Latency was measured on the 4-CPU Linux build machine (finishing a workout: p50 394.2 ms), not on
  the target Windows laptop.

## Architecture

```
┌──────────────── Electron app (apps/desktop) ────────────────┐
│ Renderer: React + TypeScript + Vite + Tailwind (sandboxed)   │
│        │ window.ascend.request()  (typed, contextBridge)     │
│ Preload ──IPC──► Main: validates, adds token, proxies        │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP 127.0.0.1:<random port>, Bearer <per-launch token>
┌────────────────────────▼──────── Sidecar (services/sidecar) ─┐
│ FastAPI modular monolith                                      │
│  workouts · nutrition · gamification · progress · coach       │
│  in-process event bus: SetLogged → muscle load + XP + quests  │
│ SQLite (WAL) + Alembic migrations    optional ─► Ollama :11434│
└───────────────────────────────────────────────────────────────┘
```

- Electron main picks a free port, generates a random token, spawns the sidecar (`uv run` in
  dev, the PyInstaller exe when installed), passes the token on **stdin**, polls `/health`,
  and restarts it with backoff if it crashes.
- The renderer never sees the token and has no Node access.
- Engines are pure functions; the coach only explains their output.

Details: [services/sidecar/README.md](services/sidecar/README.md),
[apps/desktop/README.md](apps/desktop/README.md), and the full project docs in [docs/](docs/README.md).

## Tech stack

| Part | Stack |
|---|---|
| Desktop | Electron 45 (sandboxed renderer, context isolation, fuses set at pack time), React 19, TypeScript 6.0, Vite 8, Tailwind CSS 4 |
| Engine (sidecar) | Python 3.12, FastAPI, Uvicorn, Pydantic 2, SQLAlchemy 2 + Alembic, SQLite (WAL), httpx |
| Local AI (optional) | Ollama on `127.0.0.1:11434` with `qwen3:4b`; output passes a number guard |
| Packaging | PyInstaller (sidecar exe) + electron-builder NSIS installer, built on GitHub Actions |
| Tests and quality | pytest + Hypothesis, Vitest + Testing Library + jsdom, axe-core, ruff, mypy, ESLint, commitlint |
| ML pipeline | PyTorch (MobileNetV3-Small), ONNX export with a parity gate, DVC, MLflow |
| DevOps | GitHub Actions (CI on Ubuntu and Windows, ML, Windows installer + release), Docker for sidecar tests |

Versions and the reasons for each choice: [docs/development/tech-stack.md](docs/development/tech-stack.md).

## Repository layout

```
apps/desktop/        Electron + React app
services/sidecar/    FastAPI engine, SQLite, Alembic, tests, PyInstaller spec
packages/shared/     TypeScript types: API + typed IPC contract
ml/                  food-classifier pipeline (DVC + MLflow, synthetic smoke data)
docker/              Dockerfile + compose for sidecar dev/tests
docs/                project docs: architecture, ADRs, contracts, team plan, releases
scripts/             PowerShell setup helper, contract drift and link checks, map generator
.github/             CI, ML and Windows installer workflows, issue templates, CODEOWNERS
```

## Developer quick start

You need **Git**, **Node.js 22.22.2 or newer** (22 LTS; newer works with npm) and **uv**.
The sidecar uses **Python 3.12**; uv installs it *next to* any existing Python (3.14 is fine) and
never touches it.

```powershell
# 1. uv (Python version + package manager), once
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv python install 3.12

# 2. get the code
git clone https://github.com/Lucifer-Newstar/Ascend-.git ascend
cd ascend

# 3. install everything (or run: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1)
cd services\sidecar; uv sync; uv run alembic upgrade head; cd ..\..
npm install

# 4. run the desktop app (Electron starts the sidecar for you)
npm run dev:electron -w apps/desktop
```

**If `npm run dev:electron` says "Electron failed to install correctly"** (seen on Windows with Node 26:
the download finishes but the unzip step silently fails), unzip it yourself from the repo root:

```powershell
$zip = Get-ChildItem "$env:LOCALAPPDATA\electron\Cache" -Recurse -Filter "electron-v*-win32-x64.zip" | Select-Object -First 1
Expand-Archive $zip.FullName -DestinationPath node_modules\electron\dist -Force
Set-Content node_modules\electron\path.txt "electron.exe" -NoNewline
```

### Optional AI coach

```powershell
# install Ollama from https://ollama.com, then:
ollama pull qwen3:4b        # ~2.5 GB; fits a 4 GB GPU
```

**Tuning for 4 GB GPUs (e.g. RTX 3050 Laptop).** With default settings `ollama ps` showed `qwen3:4b`
at 3.5 GB split 34%/66% CPU/GPU and 8.3 tokens/s. These three settings brought it to 21.3 tokens/s on
the same laptop (measured with `ollama run qwen3:4b --verbose`, one prompt each, Oct 2026):

```powershell
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KV_CACHE_TYPE q8_0
setx OLLAMA_CONTEXT_LENGTH 2048
# then quit Ollama from the tray and start it again
```

Toggle **AI coach** in the top bar. With it off (or Ollama not running) the coach gives
rule-based tips; nothing else changes.

### Other ways to run

```powershell
# UI in a browser (fast reload), two terminals:
cd services\sidecar; uv run python -m app --dev      # API + docs: http://127.0.0.1:8765/docs
npm run dev -w apps/desktop                          # app: http://localhost:5173

# demo data (wipes your local data first!)
cd services\sidecar; uv run python -m app.devtools.seed_demo --wipe
```

Your data (one SQLite file, `ascend.db`) lives in `%APPDATA%\ASCEND\data`, whether you run the
installed app, the dev Electron app or the sidecar on its own.

Full setup, including Docker, MLflow and troubleshooting: [docs/development/local-setup.md](docs/development/local-setup.md).

## Testing and CI

`make help` lists the developer commands (Git Bash / WSL); each is a plain command you can also
paste into PowerShell.

| | |
|---|---|
| `make check` | everything CI runs: lint, types, tests, migrations, contract drift, build |
| `make test` | pytest + vitest |
| `make lint typecheck` | ruff, eslint, mypy, tsc |
| `make build-sidecar` | PyInstaller → `services/sidecar/dist/ascend-sidecar/` |
| `make dist-win` | Windows installer → `apps/desktop/release/` (run on Windows) |
| `make docker-test` | lint + tests inside Docker |

Workflows in [.github/workflows](.github/workflows/):

- **`ci.yml`** (every push and PR, plus nightly): commit-message lint and a Markdown link check;
  ruff, mypy, pytest with coverage, Alembic on a fresh database and the contract drift check on
  Ubuntu and Windows; eslint, tsc, vitest and the Vite build on Ubuntu and Windows; the PyInstaller
  sidecar build with a smoke test; the Docker test image.
- **`ml.yml`**: ML lint and tests, and a smoke `dvc repro` of the pipeline on synthetic data.
- **`release.yml`** (pushes to `main` that touch the app, version tags `v*`, or manual): on
  `windows-latest`, builds and smoke-tests the sidecar exe, builds the NSIS installer and checks that
  all Electron fuses are set. On a version tag it publishes the installer, `SHA256SUMS.txt` and the
  notes from `docs/releases/<tag>.md` as a GitHub Release.

How a release is cut: [docs/operations/release-process.md](docs/operations/release-process.md).

### Verified for 1.0.0

On Linux, at the 1.0.0 commit:

- 666 sidecar tests pass (engine unit tests, Hypothesis property tests for the engines, API tests
  with `TestClient`); ruff and mypy are clean (108 source files).
- Alembic migrations apply to a fresh SQLite database and downgrade back to base.
- tsc (renderer, Electron, shared), eslint and 353 vitest tests (59 files) pass;
  `vite build` succeeds.
- The contract drift check passes (81 implemented operations match 9 contracts).
- ML lint and tests pass.

On GitHub Actions: the CI, ML and installer workflows are green on `main`. The Windows installer is
built on `windows-latest` with the sidecar smoke test and the fuse check; the v0.4.0 release was the
first one published with its installer.

Not covered by automation: the installed app's screens on a real Windows PC (checked by hand), real
`qwen3:4b` answers, and the live wger.de and Wikipedia APIs (tests use mocks; the live APIs were
checked by hand on 2026-10-20).

## Documentation

- [docs/README.md](docs/README.md): the map of all project documentation
- [System architecture](docs/architecture/system-architecture.md) and the
  [ADRs](docs/architecture/adr/) (22 decisions)
- [API contracts](docs/contracts/README.md) and the [IPC contract](docs/contracts/ipc-contract.md)
- [AI and ML docs](docs/ai/README.md), including the [evaluation](docs/ai/evaluation.md)
- [Security and privacy](docs/architecture/security-privacy.md) and [SECURITY.md](SECURITY.md)
- [Project proposal](docs/project/proposal.md) and [roadmap](docs/project/roadmap.md)
- Per-folder guides: [desktop](apps/desktop/README.md), [sidecar](services/sidecar/README.md),
  [ml](ml/README.md), [docker](docker/README.md), [scripts](scripts/README.md)

## Team

| | Role | Owns |
|---|---|---|
| Navin ([@Lucifer-Newstar](https://github.com/Lucifer-Newstar)) | Lead · MLOps | architecture, releases, `ml/` |
| Gokul ([@Gokul143-J](https://github.com/Gokul143-J)) | DevOps | CI/CD, Docker, packaging |
| Jegatheesan ([@jegatheesank](https://github.com/jegatheesank)) | Backend | sidecar, engines, database |
| Dhanush ([@dhanush-07-byte](https://github.com/dhanush-07-byte)) | Frontend | Electron + React UI, muscle map |

See [CONTRIBUTING.md](CONTRIBUTING.md) for branches, commit style and PR rules, and
[SECURITY.md](SECURITY.md) for how to report a vulnerability and the status of the
October 2026 security review.

## Credits and licences

- Trainer art (v8): Instructor Iskra Vey is an original character designed for ASCEND; how the images were made and their licence status are in `apps/desktop/src/assets/trainer/ART_PROVENANCE.md`.
- Muscle map artwork (v8, redrawn as v2): ASCEND's own original drawing of 54 muscles and heads,
  front, back and a deep layer, generated by `scripts/body_map/build_map.py` (MIT, like the rest of the
  repo). Versions up to v7 used react-muscle-highlighter 1.2.0 (MIT, © 2024 My Muscle
  Contributors), which is no longer a dependency.
- Fonts: Inter and Rajdhani (SIL Open Font License), bundled via `@fontsource`.
- Food values: approximate, rounded home-style figures in the style of IFCT 2017 (NIN) and the
  Indian Nutrient Databank (INDB). Not a substitute for a dietitian.
- Formulas: Mifflin-St Jeor (BMR), Epley (e1RM), MET method (calorie burn) are standard
  estimation formulas; results are estimates.
- Exercise library and exercise photos: [free-exercise-db](https://github.com/yuhonas/free-exercise-db)
  (yuhonas), **Unlicense** (public domain). One photo per exercise is bundled as a 320 px webp
  (873 files, about 5.1 MiB); 14 of ASCEND's own entries reuse the photo of a similar movement
  and say so. Exercises without a photo get a designed tile drawn by the app.
- Skill-tree progressions follow the r/bodyweightfitness Recommended Routine and wiki, Steven Low's
  *Overcoming Gravity* (2nd ed.) and GMB Fitness tutorials. The thresholds are ASCEND's own choices
  (see `docs/architecture/skill-trees.md`).
- Optional online research: [wger](https://wger.de) exercise data (CC-BY-SA 4.0) and
  [Wikipedia](https://en.wikipedia.org) summaries (CC BY-SA 4.0), only when you turn it on or allow a
  single lookup; results are credited on the exercise with a link and licence.

Parts of this codebase were written with AI assistance.

**Feature freeze after v8.** v8 is the last release that adds features. From here a change
has to fix something, reduce friction, or replace an existing feature; the reasons are in
[docs/research/v8-gamified-engagement.md](docs/research/v8-gamified-engagement.md) §4.

## Licence

[MIT](LICENSE) © 2026 The ASCEND team.
