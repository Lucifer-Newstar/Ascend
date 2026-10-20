# Phase 0 Kickoff

> The first ASCEND team meeting: what it decides, what everyone leaves with, and the
> first issues. Facilitator: Navin (script in
> [kickoff-guide.md](../members/navin-lead/kickoff-guide.md)).
> Proposed date: **Mon 26 Oct 2026, 60–75 min** (estimate; confirm in the group chat).

---

## 1. Goals of the kickoff

1. Everyone understands what ASCEND is and is **not** (offline, desktop, no cloud).
2. Roles and repo ownership are agreed ([team-structure.md](../team/team-structure.md)).
3. The decisions D1–D10 are ratified or changed ([planning/README.md §2](README.md#2-decision-log)).
4. Each member leaves with their first three issues and a working machine setup plan.

## 2. Agenda

| # | Item | Time | Owner |
|---|---|---|---|
| 1 | Pitch + product vision walk-through (mockups) | 10 min | Navin |
| 2 | Architecture in 5 minutes (processes, sidecar, event bus, AI optional) | 10 min | Navin |
| 3 | Roles, ownership, reviewers | 10 min | All |
| 4 | Decisions to ratify (§4) | 15 min | All |
| 5 | Working rules: commits, branches, PRs, AI-assistance rule | 10 min | Navin |
| 6 | First issues + setup check (§5) | 10 min | Each member |
| 7 | Sync rhythm, next gate date | 5 min | Navin |

## 3. Before the meeting (everyone)

- [ ] Read [docs/README.md](../README.md), [features.md](features.md) §1 and your member folder
- [ ] Have a GitHub account with 2FA on; accept the repo invite
- [ ] Check your laptop against [local-setup.md §1](../development/local-setup.md#1-hardware-and-os)

## 4. Decisions to ratify

| # | Question | Proposed answer |
|---|---|---|
| K1 | Accept D1–D10 as written? | Yes, with any changes logged |
| K2 | Weekly sync slot | Sunday 7:30 PM IST, 30 min |
| K3 | Package managers | `npm` (Node), `uv` (Python) |
| K4 | Merge style | Rebase-merge by default; squash for noisy branches |
| K5 | Reviews | 1 approval; 2 for contracts/architecture; reviewer replies within 48 h |
| K6 | Issue tracking | GitHub Issues + a Project board with columns Backlog / Ready / In progress / Review / Done |
| K7 | Labels | `area:*`, `phase:*`, `type:*`, `good-first-issue`, `needs-owner`, `blocked` |
| K8 | Who has a GPU? | Record in the tracker; AI work needs ≥ 4 GB VRAM or runs in rules mode |

## 5. First issues (Phase 0, week 1)

| Member | Issue 1 | Issue 2 | Issue 3 |
|---|---|---|---|
| Dhanush | `feat(desktop): Electron + Vite + React + TS scaffold` | `feat(desktop): secure BrowserWindow defaults + CSP` | `feat(ui): Tailwind tokens from design system` |
| Jegatheesan | `feat(sidecar): FastAPI app factory + /health` | `feat(core): SQLite engine with WAL pragmas` | `feat(core): Alembic baseline migration` |
| Gokul | `chore(meta): npm workspace + uv project layout` | `chore(meta): pre-commit (ruff, mypy, eslint, prettier, gitleaks)` | `ci: lint + unit tests on windows-latest and ubuntu-latest` |
| Navin | `docs: commit docs/ folder` | `chore(meta): branch protection, CODEOWNERS, PR template` | `docs(adr): ratify ADR-0001…0010 after kickoff` |

## 6. Phase 0 gate (8 Nov, estimate)

- [ ] CI-built NSIS installer installs and starts on a clean Windows user account
- [ ] Main spawns the sidecar on a random port with a token; `/health` returns `db: ok, migrations: head`
- [ ] Killing `ascend-sidecar.exe` triggers a restart with backoff (visible in logs)
- [ ] Every member has merged at least 3 PRs of their own
- [ ] Tracker items 1–8 ✅ ([tracker.md](tracker.md))

## 7. Minutes template

```text
Date / attendees:
Decisions (copy into planning/README.md §2):
Action items (owner, due):
Risks raised (copy into integration-edge-cases.md):
Next sync:
```
