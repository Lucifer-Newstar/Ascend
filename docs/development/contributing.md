# Contributing

> **Read first:** [team-structure.md](../team/team-structure.md) — who owns what ·
> [working-rules.md](../team/working-rules.md) — project rules, commit conventions, branch
> workflow, Definition of Done. New here? Start with the
> [docs reading order](../README.md#3-reading-order-for-a-new-member).

---

## 1. Workflow summary

1. **Pick an issue** from the Project board (`Ready` column) or your
   [phase plan](../members/README.md). Assign yourself; move it to `In progress`.
2. **Branch** from up-to-date `main`: `feat/<member>-<area>-<topic>`
   (e.g. `feat/dhanush-ui-rings`, `fix/jega-workouts-pr-dup`, `ci/gokul-release`).
3. **Commit small** — one logical change, Conventional Commit message
   ([working-rules §2](../team/working-rules.md#2-commit-conventions-conventional-commits)).
4. **Push and open a PR early** (draft is fine) so CI runs on every push.
5. **Request review** from the owner/reviewer in [team-structure §3](../team/team-structure.md#3-repository-ownership).
6. **Merge** when CI is green and approvals are in: the lead merges with a merge commit
   (`--no-ff`), see [branch-protection.md](branch-protection.md).
7. **Log it** in your `work-log.md` if it is user-visible or crosses lanes.

## 2. Branching model

```text
main ──●────────●──────────●──────── (protected, always releasable, tags vX.Y.Z)
        \      /  \        /
         ●──●──●    ●──●──●          short-lived feature branches (≤ 3 days)
```

- Trunk-based: no long-lived `develop` branch. Releases are tags on `main`
  ([release-process.md](../operations/release-process.md)).
- Unfinished features hide behind a settings flag rather than living on a branch for weeks.
- Hotfix: branch `fix/<member>-<topic>` from the release tag, PR into `main`, patch release.

## 3. Pull request rules

| Rule | Detail |
|---|---|
| Size | Aim for < 400 changed lines (generated files excluded). Split bigger work |
| Title | A Conventional Commit line, e.g. `feat(coach): weekly review findings` |
| Description | What and why, screenshots for UI, how you tested, linked issue (`Closes #12`) |
| Contract changes | Edit `docs/contracts/` in the same PR; label `contract`; 2 approvals |
| Architecture changes | Include an ADR; Navin must approve |
| AI assistance | Tick the checkbox honestly; you must be able to explain every line |
| Self-review | Read your own diff on GitHub before requesting review |
| CI | All required checks green; no `skip` without an issue link |

**PR template** (`.github/pull_request_template.md`):

```markdown
## What
## Why
## How I tested
## Screenshots (UI)
## Checklist
- [ ] Conventional Commit title
- [ ] Tests added/updated (formulas: golden files)
- [ ] Docs updated (index if structure changed)
- [ ] Contract changed? YAML/IPC doc updated + `contract` label
- [ ] No secrets, personal data or unlicensed media
- [ ] AI assistance used: yes / no — and I can explain all of it
```

## 4. Code review

- **Reviewer's job:** correctness, tests, readability, contract/ADR compliance, security
  (IPC, paths, SQL), honest numbers. Not style — linters do style.
- **Response time:** first review within 48 hours (proposal K5 in [kickoff.md](../planning/kickoff.md#4-decisions-to-ratify)).
- **Comment labels:** `blocking:`, `suggestion:`, `question:`, `nit:` — only `blocking`
  stops a merge.
- **Approvals:** 1 (2 for contracts, migrations, CI/release workflows, security).
- **Teach-back:** for any non-trivial PR, the reviewer may ask the author to explain a
  part in the weekly sync. This is normal, not a punishment.

## 5. CI checks on every PR

| Check | Tool | Owner |
|---|---|---|
| Python lint + format | `ruff check`, `ruff format --check` | Gokul |
| Python types | `mypy app` | Gokul |
| Python tests + coverage | `pytest --cov` (rules modules ≥ 80%) | Jegatheesan |
| Migrations | upgrade from every released fixture DB + one downgrade | Jegatheesan / Gokul |
| TypeScript lint + types | `eslint`, `tsc --noEmit` (both tsconfigs) | Dhanush |
| UI tests | `vitest run` | Dhanush |
| Contract drift | `scripts/check_contract_drift.py` + generated TS types up to date | Gokul |
| Secrets | `gitleaks` | Gokul |
| Dependencies | `npm audit --omit=dev`, `pip-audit` | Gokul |
| Docs | markdown link check + Mermaid render (`mmdc`) | Navin |
| Build (on `main` and PRs touching build files) | PyInstaller sidecar + electron-builder NSIS on `windows-latest` | Gokul |

## 6. Conventions

- **Python (`services/sidecar`, `ml`):** 3.12, `ruff` (line length 100) + `mypy`, type hints
  everywhere, Pydantic for every schema, docstrings per working-rules rule 3, formulas cite
  their spec section and carry an `ALGO_VERSION`.
- **TypeScript (`apps/desktop`, `packages/shared`):** strict mode, ESLint + Prettier, no
  `any` without a comment, React function components + hooks, Tailwind tokens only (no
  ad-hoc hex colours).
- **SQL:** through SQLAlchemy; raw SQL only in migrations; every migration reversible
  where possible.
- **Files and paths:** `pathlib` / `path.join`, never string concatenation; test with a
  non-ASCII user directory.
- **Docs:** one purpose per file; link new files from [docs/README.md](../README.md).

## 7. Definition of Done

See [working-rules.md §4](../team/working-rules.md#4-definition-of-done-per-task).
