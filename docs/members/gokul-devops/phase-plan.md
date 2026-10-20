# Gokul · DevOps Phase Plan

> **Purpose:** my delivery, handoffs and commit-sized tasks by phase. Shared scope: [features](../../planning/features.md). Gates: [phases](../../planning/phases.md). Dates (estimates): [timeline](../../planning/timeline.md). Tick a box when the commit is merged. AI tasks and their design docs: [ai-roadmap](../../ai/ai-roadmap.md).

| Phase | I deliver | I need | Handoff / completion check |
|---|---|---|---|
| **0 · Foundations** | pre-commit, CI matrix, PyInstaller sidecar + NSIS hello-world installer on CI, dev container | Skeleton (exists) | CI-built installer installs and starts on a clean Windows user |
| **1 · Core loop** | Coverage gate, contract-drift job, migration fixture tests, docs checks, MLflow Compose, caches | Contracts, fixtures from Jegatheesan | Drift job fails on a deliberate mismatch; fixture upgrade green |
| **2 · Local AI** | ML training image (CUDA), Prometheus/Grafana Compose, AI tests marked and split | Metrics names from Jegatheesan | Navin trains in the image on the RTX 3050; dashboard shows latency |
| **3 · Ship v1.0** | Release workflow, update channels, SBOM + checksums, packaged smoke test, egress test, rollback drill support | Release decisions from Navin | `v1.0.0` released by the workflow; drill recorded |
| **4 · Breadth** | Playwright journeys + visual regression in CI; optional kind + Helm lab for MLflow | Screens from Dhanush | E2E stable (< 2% flaky) |
| **5 · MLOps loop** | `model-release.yml`, manifest publishing | Promoted model from Navin | Model-only update reaches the app |

## Commit-sized tasks

### Phase 0 · Foundations (26 Oct – 8 Nov)

- [x] `chore(meta): .gitattributes for LF and binary files`
- [x] `chore(meta): pre-commit with ruff, mypy, eslint, prettier, gitleaks` — ruff, mypy, eslint, gitleaks and commit-msg in; prettier left out until the team agrees a style
- [x] `ci: python job (ruff, mypy, pytest) with uv cache` — existed in the skeleton; artifacts now named per OS/SHA with a coverage summary
- [x] `ci: node job (eslint, tsc, vitest) with npm cache` — existed in the skeleton
- [x] `ci: run both jobs on windows-latest and ubuntu-latest`
- [x] `build: review and harden the PyInstaller one-folder spec (services/sidecar/packaging)` — dev tooling excluded, optimize=1, Windows version info; `packaging/smoke.py` checks a build
- [ ] `ci: build sidecar on windows-latest and upload artefact`
- [x] `build: electron-builder NSIS per-user config with sidecar in extraResources` — plus app icons; data kept on uninstall
- [x] `ci: build hello-world installer artefact on main` — on app-touching pushes to main and on tags
- [x] `build: Electron fuses (RunAsNode off, ASAR integrity)` — afterPack hook, verified with `electron-fuses read`
- [ ] `chore(infra): dev container with Python 3.12 and Node LTS`
- [x] `chore(meta): Dependabot for npm, uv and GitHub Actions`

### Phase 1 · Core loop (9 Nov – 13 Dec)

- [ ] `ci: coverage gate 80% on rules modules`
- [x] `ci: contract drift check against docs/contracts via manifest.json` — fails on a mismatch: it found real drift on its first run, fixed in the same PR
- [ ] `ci: regenerate OpenAPI TS types and fail if stale`
- [ ] `ci: migration upgrade test from fixture databases`
- [ ] `ci: import-linter layering contracts`
- [ ] `ci: docs job (markdown link check + mermaid render)`
- [ ] `ci: gitleaks, npm audit and pip-audit on PRs`
- [ ] `build(infra): MLflow Compose with local artefact volume` (pair: Navin)
- [ ] `ci: pin all actions by commit SHA`
- [ ] `perf(ci): split fast ubuntu jobs from windows build jobs`

### Phase 2 · Local AI (14 Dec – 17 Jan)

- [ ] `build(infra): ML training Dockerfile (CUDA, PyTorch, timm) for WSL2 GPU`
- [ ] `docs(infra): GPU-in-Docker check and troubleshooting`
- [ ] `build(infra): Prometheus + Grafana Compose for the dev sidecar`
- [ ] `feat(infra): Grafana dashboard JSON (latency, jobs, tokens/s)`
- [ ] `ci: mark GPU tests and skip them on hosted runners`
- [ ] `ci: ml-eval workflow skeleton on tagged models` (pair: Navin)
- [ ] `ci: ai-safety job runs the 40-message safety suite on every PR`
- [ ] `ci: ai-eval-report job checks prompt hashes, model digest and thresholds`

### Phase 3 · Ship v1.0 (18 Jan – 7 Feb)

- [ ] `ci: release workflow on v* tags (sidecar → installer → draft release)`
- [ ] `ci: SHA256SUMS and CycloneDX SBOM attached to releases`
- [ ] `ci: verify release assets and latest.yml before publish`
- [ ] `feat(desktop): electron-updater with stable and beta channels` (pair: Dhanush)
- [ ] `test(e2e): silent install + launch + log a set smoke test`
- [ ] `test(e2e): egress-blocked run fails on non-localhost connections`
- [ ] `ci: protected release environment with Navin as reviewer`
- [ ] `chore(scripts): release.ps1 bumps versions in both manifests and tags`
- [ ] `docs(operations): rollback drill timings` (pair: Navin)
- [ ] `ci: bundle classifier + manifest in the installer and verify SHA-256`

### Phase 4 · Breadth (8 Feb – 21 Mar)

- [ ] `ci: Playwright for Electron journeys on windows-latest`
- [ ] `ci: visual regression with approved baselines` (pair: Dhanush)
- [ ] `ci: flaky-test report and auto-retry once`
- [ ] `feat(infra): kind cluster + Helm chart for MLflow (optional lab)`

### Phase 5 · MLOps loop (22 Mar – 16 May)

- [ ] `ci: model-release workflow uploads ONNX + labels and updates manifest`
- [ ] `ci: manifest schema validation and min_app_version check`
- [ ] `ci: model-release workflow publishes sha256sums.txt and the manifest`

## DevOps completion check (each phase)

- [ ] Required checks enforced by branch protection
- [ ] CI time within budget (< 12 min PR)
- [ ] Installer artefact built from `main` and installable
- [ ] Work log updated; demo given at the gate
