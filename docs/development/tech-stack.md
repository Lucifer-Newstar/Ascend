# Tech Stack

> The chosen technologies, the version line we target, and why. Decisions with real
> trade-offs have ADRs. Versions marked "v0.1" are what the code skeleton pins today;
> upgrade by PR. Owner: Navin.

---

## 1. Desktop app (`apps/desktop`, `packages/shared`)

| Layer | Choice | Version line | Why |
|---|---|---|---|
| Shell | Electron | `^33` (v0.1); move to a currently supported major before v1.0 | Web UI + native Windows features ([ADR-0001](../architecture/adr/0001-electron-react-desktop.md)) |
| UI | React + TypeScript (strict) | React 18, TS 5.6 (v0.1) | Team skills; mockups are HTML/CSS |
| Build | Vite | 5 (v0.1) | Fast dev server, simple config |
| Styling | Tailwind CSS + shadcn/ui (Radix) | Tailwind 4 (v0.1) | Design tokens, accessible primitives |
| Icons / fonts | lucide · Inter, Rajdhani (`@fontsource`) | — | Offline fonts bundled |
| Charts | Recharts | — | Simple, SVG |
| Muscle map | Original SVG artwork, 54 muscles and heads with a deep layer (`lib/bodyMapPaths.ts`, v8); `react-muscle-highlighter` 1.2.0 up to v7 | v8 | MIT, see ADR-0021 |
| Data fetching | TanStack Query | — | Caching, retries, invalidation on SSE events |
| Validation | zod | — | IPC payload validation in main |
| Tests | Vitest + Testing Library · Playwright for Electron | Vitest 2 (v0.1) | Unit + E2E |
| Packaging | electron-builder (NSIS) + electron-updater | 25 (v0.1) | [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md) |
| Workspaces | npm workspaces | npm ≥ 10 | Already used by the skeleton |

## 2. Sidecar (`services/sidecar`)

| Layer | Choice | Version line | Why |
|---|---|---|---|
| Language | Python | **3.12** (`.python-version`) | ML/packaging libraries support it; 3.14 too new for parts of the stack ([ADR-0002](../architecture/adr/0002-fastapi-python-sidecar.md)) |
| Env / deps | uv | latest | Fast, installs 3.12 side by side, lockfile (`uv.lock`) |
| API | FastAPI + Uvicorn | FastAPI ≥ 0.115 | OpenAPI for free, Pydantic |
| Schemas | Pydantic v2 | ≥ 2.7 | Contracts source of truth |
| DB | SQLite + SQLAlchemy 2 + Alembic | SQLAlchemy ≥ 2.0.30, Alembic ≥ 1.13 | [ADR-0003](../architecture/adr/0003-sqlite-local-only.md) |
| HTTP client | httpx | ≥ 0.27 | Ollama calls with timeouts |
| Inference | ONNX Runtime (CPU) | — (Phase 2) | Classifier without PyTorch in the app |
| Logging | structlog | — (Phase 1) | JSON lines, correlation ids |
| Tests / quality | pytest, pytest-cov, Hypothesis, ruff, mypy, import-linter | pytest ≥ 8.2 | Rules are tested like maths |
| Packaging | PyInstaller one-folder | ≥ 6.10 | [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md) |

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
| PyTorch + timm | Training (CUDA in Docker on WSL2) |
| DVC | Dataset + pipeline versioning; local/external-drive remote |
| MLflow | Tracking + model registry (Docker Compose) |
| ONNX | Export + parity test |
| Docker Desktop (WSL2 backend) | Training image, MLflow, Prometheus/Grafana |
| GitHub Actions | `ml-eval.yml` evaluation gate |

## 5. DevOps

| Area | Choice |
|---|---|
| CI/CD | GitHub Actions (`windows-latest` for builds and E2E, `ubuntu-latest` for fast jobs) — free for public repos on standard runners |
| Releases + updates | GitHub Releases + electron-updater (`latest.yml`, blockmaps) |
| Supply chain | gitleaks, npm audit, pip-audit, CycloneDX SBOM, SHA-256 checksums, Dependabot, actions pinned by SHA |
| Dev observability | Prometheus + Grafana (Compose), dev builds only |
| Docs | Markdown + Mermaid/PlantUML, link check + `mmdc` render in CI |
| Code signing | Undecided (unsigned at first; see [ADR-0008](../architecture/adr/0008-electron-builder-pyinstaller-packaging.md)) |

## 6. What we deliberately do not use

Kubernetes, Terraform, cloud databases, Redis, message brokers, analytics SDKs, crash
upload services. ASCEND is a single-user desktop app; these add cost and risk without a
user benefit. (Kubernetes appears only as an **optional** Phase 4 learning lab for the
MLflow stack — see [phases.md](../planning/phases.md).)
