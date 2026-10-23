# Gokul J — DevOps Engineer

> **Member 3** — DevOps track: everything that builds, checks, packages and ships ASCEND.

## Role

Make every push trustworthy and every release boring: CI that catches problems in
minutes, a Windows installer built from week two, auto-updates from GitHub Releases, and
the Docker images the team uses for ML and dev observability. Works closely with the
Team Lead, who decides releases and owns the MLOps pipeline that runs on this
infrastructure.

## Primary responsibilities

- Repo tooling: npm workspaces + uv layout, pre-commit (ruff, mypy, eslint, prettier,
  gitleaks), `.gitattributes`, Dependabot security alerts, actions pinned by SHA
- **CI** (GitHub Actions): lint → types → unit → integration → migration upgrade tests →
  contract drift → build sidecar → build installer → packaged smoke test; caches; matrix
  `windows-latest` + `ubuntu-latest`
- **Packaging:** PyInstaller one-folder sidecar (`services/sidecar/packaging/ascend-sidecar.spec`), electron-builder
  NSIS per-user installer, Electron fuses, app icons, `AppUserModelID`
- **Release automation:** `release.yml`, asset verification, SHA-256 + CycloneDX SBOM,
  `latest.yml`/blockmaps, beta/stable channels, `model-release.yml` (Phase 5)
- **Docker:** dev container (Python 3.12 + Node pinned), ML training image (CUDA +
  PyTorch, for Navin), Compose for MLflow and Prometheus/Grafana
- Dev-time observability: `/metrics` dashboards; egress-blocked E2E test
- Playwright for Electron in CI and visual regression (with Dhanush)

## Repo areas owned

- `.github/` (workflows, PR template, CODEOWNERS with Navin), `build/`, `services/sidecar/packaging/`, `infra/`, `scripts/` (CI scripts)
- `docs/development/local-setup.md` (keep it working), `docs/operations/release-process.md` (automation sections)
- `docs/members/gokul-devops/` (this folder)

## Contracts I consume / provide

| Contract | Direction | Counterpart |
|---|---|---|
| Sidecar entry point, deps groups (`uv sync --group build`) | consume | Jegatheesan |
| Electron build config, resources path for the sidecar | consume | Dhanush |
| Release decisions (version, go/no-go, channel) | consume | Navin |
| Training image + MLflow Compose | **provide** | Navin |
| CI pipeline, required checks, caches | **provide** | everyone |
| Installer, update channels, release assets | **provide** | Navin (publishes), users |
| Fixture DB + golden-file CI jobs | **provide** | Jegatheesan |

## My commitments

- `main` is always green; a red `main` is fixed or reverted the same day.
- Every release asset has a checksum and an SBOM; nothing publishes without verification.
- CI stays under 12 minutes for a PR (target).
- I can walk an interviewer from `git tag` to a user's auto-update and explain every step.
