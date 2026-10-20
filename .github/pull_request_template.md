<!-- Title: a Conventional Commit line, e.g. "feat(progress): body measurement endpoints" -->

## What

<!-- One or two sentences: what changes for the user or the codebase. -->

## Why

<!-- Link the phase-plan task or issue: Closes #12 / docs/members/<you>/phase-plan.md -->

## How I tested

- [ ] `make check` (ruff, mypy, pytest, eslint, tsc, vitest, vite build) passes locally
- [ ] Tried it in the running app (`make dev-sidecar` + `make dev-web`) — describe the clicks:

## Screenshots (UI changes)

## Checklist

- [ ] Commit messages follow Conventional Commits (commitlint passes)
- [ ] Tests added or updated (formulas: golden values + an `ALGO_VERSION` bump)
- [ ] New migration applies to a fresh database (`make migrate-fresh`)
- [ ] Contract changed? `docs/contracts/*.yaml` updated in this PR
- [ ] Phase-plan box ticked and a work-log row added
- [ ] AI-assisted code: I can explain every line I am submitting
