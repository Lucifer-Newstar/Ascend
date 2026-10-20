# Working Rules

> The non-negotiable rules of the ASCEND project and the git conventions the whole
> team follows. Every member reads this before their first commit.
>
> Maintainer: Member 4 (Team Lead).

---

## 1. The Project Rules

| # | Rule | What it means in practice |
|---|------|---------------------------|
| 1 | **Document everything** | Design, decisions, experiments and setup steps go into `docs/` as part of the work, not after it. |
| 2 | **Keep the docs folder clean** | Every file has one purpose and a home; the [docs index](../README.md) is updated when structure changes; links stay green. |
| 3 | **Comment the code** | Module docstrings, function docstrings, and a comment on any non-obvious logic (every formula cites its spec section). |
| 4 | **Real commit history** | Small, logical, well-messaged commits, dated when the work actually happens. No backdating, no squashing someone else's work into your name. |
| 5 | **Offline by default** | No code path sends user data off the PC. Network calls are limited to opt-in model downloads and the update check ([ADR-0009](../architecture/adr/0009-offline-first-no-cloud.md)). |
| 6 | **Rules decide, AI explains** | No number shown to the user is produced by a language model ([ADR-0005](../architecture/adr/0005-deterministic-engines-llm-explains.md)). |
| 7 | **Own what you merge** | AI assistance is allowed and disclosed; you must be able to explain any line you commit. Tick the PR checkbox honestly. |
| 8 | **Honest numbers** | Estimates are labelled as estimates; measured numbers carry a date and a link to the run. |
| 9 | **Original IP only** | No names, art, logos or signature terms from existing anime, manhwa or games. |

---

## 2. Commit Conventions (Conventional Commits)

Format: `<type>(<scope>): <subject>`

| Type | Use for |
|---|---|
| `feat` | a new feature or component |
| `fix` | a bug fix |
| `docs` | documentation only |
| `refactor` | code change with no behaviour change |
| `test` | tests only |
| `perf` | performance improvement |
| `ci` | GitHub Actions workflows |
| `build` | packaging (PyInstaller, electron-builder), dependencies |
| `chore` | tooling and housekeeping |

**Scopes** (match repo areas): `desktop`, `ui`, `ipc`, `sidecar`, `core`, `workouts`,
`nutrition`, `gamification`, `coach`, `progress`, `io`, `ai`, `ml`, `infra`, `ci`,
`build`, `release`, `docs(<sub>)` (e.g. `docs(adr)`), `meta` (root files).

```text
feat(workouts): detect e1RM PRs with Epley and Brzycki
fix(desktop): restart sidecar with backoff after 3 missed health checks
ci: run vitest and pytest on windows-latest
feat(ml): log baseline classifier run to MLflow
docs(adr): add ADR-0011 for SQLCipher encryption
```

**Rules**

- One logical change per commit. Subject ≤ 72 characters, imperative, no trailing period.
- The body explains *why*. Reference the issue: `Refs #42` / `Closes #42`.
- Breaking contract change: `feat(workouts)!: …` plus a `BREAKING CHANGE:` footer and an ADR.
- Commit at every completed step; push at least daily when you are working.

---

## 3. Branch Workflow

- `main` is always releasable and protected: PR required, CI green, 1 approval
  (2 for contract or architecture changes), linear history.
- Branch names: `feat/<member>-<area>-<topic>`, e.g. `feat/dhanush-ui-muscle-map`,
  `fix/jega-workouts-pr-duplicates`, `ci/gokul-release-workflow`, `ml/navin-classifier-v0`.
- Keep branches short-lived (≤ 3 days). Rebase on `main` before asking for review.
- **Squash-merge** noisy branches; **rebase-merge** branches whose commits are each
  meaningful (preferred, so individual commits stay in history).
- Release tags `vX.Y.Z` are created only by the release workflow
  ([release-process.md](../operations/release-process.md)).
- Delete branches after merge.

---

## 4. Definition of Done (per task)

- [ ] Code/config/docs written with comments (rule 3)
- [ ] Tests added or updated; formulas have golden-file tests
- [ ] Docs updated in the right `docs/` sub-folder (rules 1, 2)
- [ ] Contract changed? OpenAPI/IPC doc updated in the same PR, mock regenerated
- [ ] Conventional Commit messages (rule 4)
- [ ] CI green
- [ ] No unrelated changes; no secrets, personal data or real user photos committed
- [ ] Your work log has a line for anything user-visible or cross-lane

---

## 5. Meetings and Communication

| What | When | Length |
|---|---|---|
| Weekly sync | Sunday evening (proposed) | 30 min |
| Demo of the week | Inside the sync | 5 min per member |
| Phase gate review | Last sync of each phase | 45 min |
| Ad-hoc pairing | Any time, announced in chat | — |

Decisions made in chat are copied into the issue/PR or the decision log within a day.

---

## 6. What Never Goes in the Repo

Passwords, tokens, signing certificates, `.env` files, real user data, unlicensed
photos, personal phone numbers or addresses, model weights (they are downloaded and
checksum-verified; datasets live in DVC, not git).
