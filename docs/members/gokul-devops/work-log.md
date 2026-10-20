# Gokul · Work log

> Dated record of DevOps / CI / packaging delivery. One row per merged change that is user-visible or
> crosses lanes. Newest at the bottom. Link the PR. Keep it factual: what shipped, not
> what is planned.

| Date | What I shipped | PR / evidence | Notes (handoff, follow-up) |
|---|---|---|---|
| 2026-10-20 | CI on all branches + PRs + nightly; Windows/Ubuntu matrix; artifact names per OS/SHA; coverage summary | PR #2 (`ci/foundations`) | Main keeps one run per commit; other refs cancel superseded runs |
| 2026-10-20 | commitlint job + config, PR template, issue forms, Dependabot, gitleaks/mypy hooks, `make check` | PR #2 | Whole history lints clean; everyone should run `make hooks` once |
