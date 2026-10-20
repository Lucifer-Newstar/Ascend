# Gokul · Work log

> Dated record of DevOps / CI / packaging delivery. One row per merged change that is user-visible or
> crosses lanes. Newest at the bottom. Link the PR. Keep it factual: what shipped, not
> what is planned.

| Date | What I shipped | PR / evidence | Notes (handoff, follow-up) |
|---|---|---|---|
| 2026-10-20 | CI on all branches + PRs + nightly; Windows/Ubuntu matrix; artifact names per OS/SHA; coverage summary | PR #2 (`ci/foundations`) | Main keeps one run per commit; other refs cancel superseded runs |
| 2026-10-20 | commitlint job + config, PR template, issue forms, Dependabot, gitleaks/mypy hooks, `make check` | PR #2 | Whole history lints clean; everyone should run `make hooks` once |
| 2026-10-20 | Contract drift check (scripts/check_contract_drift.py) in CI and `make check`; ML workflow for Navin's pipeline | PR #15 (`ci/contract-drift`), PR #12 | First run (re-run on 6a7670e) reports 13 drifts: 10 schema mismatches and 3 stale manifest counts; Jegatheesan synced the contracts |
| 2026-10-20 | Installer: app icons, per-user NSIS config, Electron fuses, hardened PyInstaller spec + smoke test, installer artefact on main | PR #19 (`build/packaging-release`) | Built and smoke-tested the sidecar on Linux; the NSIS installer itself still needs its first run on Windows |
| 2026-10-20 | Docker: hardened runtime image (UID 10001, read-only root, caps dropped), compose profiles test/dev/web/ml incl. MLflow, make docker-* targets, CI docker job with hadolint + runtime health check, pre-commit hadolint/contract-drift, Dependabot for Docker + ML | PR #22 (`build/docker-profiles`) | Ran every profile locally: tests pass in the container, web renders against the containerised API, MLflow accepts an experiment |
