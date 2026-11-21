# Functional verification, 22 November 2026

Status: completed checks listed below; **not** a full Windows release sign-off. Prepared on Linux for PR #34, based on `24ced89`, with the action-card synchronization and compatible lockfile updates included alongside this report. The final commit containing this report identifies the tested source changes.

## What passed

| Check | Observed result |
|---|---|
| Python unit suite | 686 collected cases passed |
| Selected API and repository-rule suites | 121 collected cases passed; list below |
| Python lint and format | Ruff passed; 393 files already formatted |
| Python types | mypy passed for 197 source files |
| Frontend suite after the action-card fix | 613 tests across 92 files passed |
| Frontend lint | Exit 0, no errors; 22 existing React/hooks warnings remain |
| Frontend/shared/Electron types | Passed |
| Production renderer and Electron main/preload build | Passed on Linux; this is not a packaged Windows installer |
| Development-tooling high advisories | Reduced from 2 to 0 by compatible lockfile updates |
| Runtime-dependency audit | `npm audit --omit=dev` reported 0 advisories at this check |

Commands used: `pytest tests/unit -q`; the selected API/rule files below with `pytest -q`; `ruff check .`; `ruff format --check .`; `mypy app`; root `npm run lint`, `npm run typecheck`, `npm test` and `npm run build`. Python 3.12.16 and Node 22.23.5 were used. The existing full Python suite was not completed as a single run here; do not describe this as every backend test passing. No Python lockfile update is included.

Selected API/rule scope: `tests/api/test_actions.py`, `test_activity_logging.py`, `test_nutrition_game.py`, `test_profile.py`, `test_intelligence_recovery.py`, `test_intelligence_progression.py`, `test_intelligence_explain.py`, `test_import.py`, `test_backup.py`, `test_export_complete.py`, `test_restore_trust.py`, `test_erase.py`, `test_backup_robustness.py`, `test_intelligence_diet.py`, plus `tests/rules`.

## Real renderer + sidecar journey

A separate disposable SQLite profile was created for testing. The real React renderer was opened in headless Chrome at 1440 by 1000 against the real running FastAPI sidecar using the browser-development proxy, not mocked API responses. AI was disabled in settings, and browser requests outside localhost/data/blob origins were blocked. This is not an OS-wide disconnected-network certification.

Observed sequence:

1. A fictional profile created through the API was shown on Today; dashboard and trainer chat rendered.
2. The user entered a bench-workout command in the visible Chat input. A confirmation card appeared.
3. The backend active workout remained `null` before confirmation.
4. Clicking the visible Confirm control created exactly three workout sets.
5. Navigating away from Chat and back preserved the executed state and Undo control after the fix.
6. Clicking Undo removed all three sets. The active workout contained zero sets.
7. No browser JavaScript errors were recorded in this journey. Screenshots were inspected for Today, proposal and executed card.

This checks the development renderer-to-API path. It does not exercise Electron IPC, the installed binary's authentication boundary, the Windows installer, first-run UI onboarding, all meal/plan screens, OS restart, every backup-restore path or real Ollama phrasing end to end. The API suites cover additional profile, meal, explanation, backup/import, erase and action cases but are not substitutes for those remaining installed-app checks.

## Defect found and fixed

The action result previously lived only in a mounted `ActionCard`. The conversation retained the original proposed state, so returning to Chat could display Confirm for an already-executed or undone action. The backend rejected repeated confirmation, preventing a duplicate write, but the UI was misleading.

A new regression test reproduced this failure before the fix. Action results now update the shared conversation, and action cards remount from the shared status in both views. The regression verifies executed/undone state across chat remounts and one confirmation call. It and the full frontend suite passed after the fix; the real renderer journey also retained executed state after navigation.

## Dependency changes and remaining warnings

Only these lockfile package entries changed:

- `joi` 18.3.0 to 18.3.2, compatible with its existing dependency range.
- `follow-redirects` 1.16.1 to 1.16.3, compatible with its existing dependency range.

Both are pulled through the `wait-on` development-tool chain. References: [joi advisory](https://github.com/advisories/GHSA-4528-x5fx-h6hg), [follow-redirects advisory](https://github.com/advisories/GHSA-mrwp-f3q8-3g9p).

Fourteen moderate development-tooling audit findings remain at this check. Some suggested remediation involves a breaking `electron-builder` downgrade; no forced downgrade or blanket audit suppression was applied. Existing lint/config deprecation warnings also remain. A clean runtime-dependency audit does not mean the application has undergone a security audit or has no vulnerabilities.

## Still required before a release or stronger academic claim

- Latest PR CI checks must pass; local results are not a CI-green claim.
- Complete the [installed Windows checklist](academic-demo.md), including installer identity, offline core journey, persistence and isolated restore evidence.
- Complete any remaining backend suite/packaging/contract/migration checks in CI and inspect failures.
- Keep food-photo recognition excluded until a model is actually trained and passes the relevant gates/licence checks.
- Keep synthetic evaluation separate from real-user or physiological validation. The [auditable decision-loop angle](proposal-auditable-decisions.md) remains a proposal, not an efficacy result.
