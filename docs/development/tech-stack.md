# Tech Stack

> The chosen technologies, the versions the repo uses at **1.0.0**, and why. Decisions with
> real trade-offs have ADRs. Rows marked **planned** were chosen in the design phase and are
> not part of the 1.0.0 app. The ML rows were updated on 2026-10-27 for the unreleased work on
> `main` (intent router, knowledge base, the food-photo runtime). Owner: Navin.

---

## 1. Desktop app (`apps/desktop`, `packages/shared`)

| Layer | Choice | Version (1.0.0) | Why |
|---|---|---|---|
| Runtime for the toolchain | Node.js + npm workspaces | Node ≥ 22.22.2 (`engines`), npm ≥ 10 | jsdom 30 needs 22.22+; workspaces share types |
| Shell | Electron | **45.0.0** (pinned) | Web UI + native Windows features, a supported major ([ADR-0001](../architecture/adr/0001-electron-react-desktop.md)) |
| UI | React + TypeScript (strict) | React 19.3, TypeScript ~6.0.3 | Team skills; mockups are HTML/CSS |
| Build | Vite + @vitejs/plugin-react | Vite 8 | Fast dev server, simple config |
| Styling | Tailwind CSS (`@tailwindcss/vite`), own design tokens | Tailwind 4 | Tokens in `src/index.css`; components are our own |
| Icons / fonts | Own SVG icons (`components/Icons.tsx`) · Inter, Rajdhani (`@fontsource`) | — | Offline, no icon font |
| Charts | Own SVG charts (`components/charts.tsx`) | — | Small, no chart library |
| Muscle map | Original SVG artwork, 54 muscles and heads with a deep layer (`lib/bodyMapPaths.ts`, v8); `react-muscle-highlighter` 1.2.0 up to v7 | v8 | MIT, see ADR-0021 |
| Data fetching | Typed client (`src/api/client.ts`): IPC in Electron, `fetch` in browser dev mode | — | One code path, no extra library |
| IPC validation | Hand-written checks in the main process (`electron/main.ts`, `electron/ipc-validate.ts`) | — | The renderer is treated as untrusted input |
| Tests | Vitest + Testing Library + jsdom, axe-core for accessibility | Vitest 5, jsdom 30 | Unit and component tests; Electron checked by hand |
| Lint | ESLint + typescript-eslint + react-hooks | ESLint 10 | |
| Packaging | electron-builder (NSIS) + `@electron/fuses` | electron-builder 26, fuses 2 | [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md); no auto-updater in 1.0.0 |

## 2. Sidecar (`services/sidecar`)

| Layer | Choice | Version line | Why |
|---|---|---|---|
| Language | Python | **3.12** (`.python-version`) | ML/packaging libraries support it; 3.14 too new for parts of the stack ([ADR-0002](../architecture/adr/0002-fastapi-python-sidecar.md)) |
| Env / deps | uv | latest | Fast, installs 3.12 side by side, lockfile (`uv.lock`) |
| API | FastAPI + Uvicorn | FastAPI 0.150, Uvicorn 0.54 (locked) | OpenAPI for free, Pydantic |
| Schemas | Pydantic v2 | 2.14 | Contracts source of truth |
| DB | SQLite (WAL) + SQLAlchemy 2 + Alembic | SQLAlchemy 2.1, Alembic 1.20 | [ADR-0003](../architecture/adr/0003-sqlite-local-only.md) |
| HTTP client | httpx | 0.28 | Ollama and opt-in online lookups, with timeouts |
| Inference | ONNX Runtime (CPU), numpy, Pillow | onnxruntime 1.31 (`uv.lock`, added after 1.3.0) | Food-photo suggestions without PyTorch in the app. The runtime ships; no food model is trained yet, so Scan meal stays hidden |
| Logging | Standard `logging` | — | structlog was planned and not adopted |
| Tests / quality | pytest, pytest-cov, Hypothesis, ruff, mypy | pytest ≥ 8.2 | Rules are tested like maths |
| Packaging | PyInstaller one-folder | ≥ 6.10 | [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md) |

The "Version" column is what `uv.lock` resolves at 1.0.0; `pyproject.toml` keeps lower bounds.

## 3. AI runtime

| Component | Choice | Why |
|---|---|---|
| LLM/VLM runtime | Ollama (user-installed, `127.0.0.1:11434`) | Simple local API, GPU offload, model store ([ADR-0004](../architecture/adr/0004-ollama-qwen3-local-llm.md)) |
| Coach | `qwen3:4b` (2.5 GB), thinking off | Tamil on Qwen3's language list; Apache-2.0; fits 4 GB |
| Meal items (optional second opinion) | `qwen3-vl:2b` (1.9 GB) | Small VLM for item lists + boxes, only when the user asks ([ADR-0012](../architecture/adr/0012-classifier-first-meal-scan.md)) |
| Lite | `qwen3:1.7b` (1.4 GB) | OOM / low-end fallback |
| Food classifier | Own CNN → ONNX | [ADR-0006](../architecture/adr/0006-own-food-classifier-indb-ifct.md) |
| Translation fallback | IndicTrans2 distilled (~200M, MIT) | Only if Tamil tests poorly — **unverified on our hardware** |

Sizes are from the Ollama tag pages (Oct 2026); speeds on the reference laptop are
**not yet measured** (Phase 2 benchmark).

## 4. ML / MLOps (`ml/`, `infra/`)

| Tool | Use |
|---|---|
| PyTorch + torchvision (MobileNetV3-Small) | Food-photo training; CPU wheels for the smoke run, the CUDA build on the training PC from the `cu126` index (torch 2.14.1 has no `cu128` wheel) |
| scikit-learn | Intent router: TF-IDF n-grams + logistic regression, exported to a JSON weights file the sidecar runs with the standard library |
| BM25 (own code, standard library) | Knowledge-base retrieval in the sidecar (`app/modules/ml/knowledge.py`) |
| DVC | Dataset + pipeline versioning; local/external-drive remote |
| MLflow | Tracking + model registry (Docker Compose) |
| ONNX | Export + parity test |
| Docker Desktop (WSL2 backend) | Training image, MLflow, Prometheus/Grafana |
| GitHub Actions | `ml.yml`: lint, tests, the labels → food table check, a smoke `dvc repro gate` on synthetic data that must not pass the gate, and a nightly intent + knowledge-base rebuild |

## 5. DevOps

| Area | Choice |
|---|---|
| CI/CD | GitHub Actions (`windows-latest` for builds and E2E, `ubuntu-latest` for fast jobs) — free for public repos on standard runners |
| Releases | GitHub Releases from `release.yml` on `v*` tags: the NSIS installer, `SHA256SUMS.txt` and notes from `docs/releases/`. No auto-updater in 1.0.0 (users download the new installer) |
| Supply chain | Actions pinned by commit SHA, read-only workflow token (write only in the publish job), SHA-256 checksums on releases, GitHub security alerts, `npm audit` by hand. gitleaks, pip-audit and an SBOM were planned and are not in CI |
| Dev observability | Planned (Prometheus + Grafana); not built |
| Docs | Markdown + Mermaid; relative-link check in CI (`scripts/check_md_links.py`) |
| Code signing | Unsigned in 1.0.0 (SmartScreen "More info → Run anyway"); see [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md) |

## 6. What we deliberately do not use

Kubernetes, Terraform, cloud databases, Redis, message brokers, analytics SDKs, crash
upload services. ASCEND is a single-user desktop app; these add cost and risk without a
user benefit. (Kubernetes appears only as an **optional** Phase 4 learning lab for the
MLflow stack — see [phases.md](../planning/phases.md).)
