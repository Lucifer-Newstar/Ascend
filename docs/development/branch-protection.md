# Branch protection and the PR flow

> **Owner:** Navin (lead). **Applies to:** `main` on GitHub. Related: [contributing.md](contributing.md),
> [decision log D14](../planning/README.md#2-decision-log), [CODEOWNERS](../../.github/CODEOWNERS).

## 1. The flow in one picture

```
feat/backend-cardio ──●──●──●──┐
                               ▼  PR #N (CI green + CODEOWNERS review)
main ──────────────────────────●  "Merge PR #N: <title> (reviewed by @Lucifer-Newstar)"
```

1. Branch from an up-to-date `main`: `feat/<area>-<topic>`, `fix/<area>-<topic>`, `ci/<topic>`,
   `chore/<topic>` or `docs/<topic>`.
2. Commit in small conventional-commit steps (`feat(progress): …`, `test(io): …`). commitlint
   checks the format in CI.
3. Open a PR into `main`. The template asks for what changed, how it was tested and which
   phase-plan box it ticks.
4. CODEOWNERS requests the owner of every touched folder. The lead (@Lucifer-Newstar) reviews
   every PR.
5. The lead merges with **Create a merge commit** (never squash or rebase), so the branch history
   and the merge both stay visible.

## 2. Settings for `main` (GitHub → Settings → Branches → Add rule)

| Setting | Value | Why |
|---|---|---|
| Require a pull request before merging | on, 1 approval | No direct pushes to `main` |
| Require review from Code Owners | on | The folder owner sees every change to their area |
| Dismiss stale approvals on new commits | on | An approval covers the code that was reviewed |
| Require status checks to pass | `Sidecar (lint, types, tests)`, `Desktop (lint, types, tests, build)`, `Commit messages` | `main` stays green |
| Require branches to be up to date | on | The checks ran against the code that lands |
| Allow merge commits | on; squash and rebase **off** | One merge commit per PR (D14) |
| Allow force pushes / deletions | off | History is never rewritten |

The lead keeps admin rights for emergencies only; an emergency fix still goes through a PR.

## 3. Reviewing a PR (lead checklist)

- [ ] CI green, including the migration check on a fresh database
- [ ] Contract changes have a matching `docs/contracts/*.yaml` change
- [ ] New formulas carry a version constant and a golden test
- [ ] The phase-plan box is ticked and the work-log row is added in the same PR
- [ ] No secrets, tokens, personal data or real photos in the diff

## 4. Merge message format

```
Merge PR #<n>: <PR title> (reviewed by @Lucifer-Newstar)
```

GitHub writes `Merge pull request #<n> from <user>/<branch>` by default; edit the title in the
merge dialog so `git log --merges --oneline` reads as a changelog.
