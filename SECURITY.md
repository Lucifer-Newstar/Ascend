# Security

ASCEND is a local-only Windows desktop app: a React renderer in Electron, a Python
(FastAPI) sidecar on `127.0.0.1`, and a SQLite database under `%APPDATA%\ASCEND`. There
is no server, account or telemetry. The threat model, hardening rules and privacy
commitments are in [docs/architecture/security-privacy.md](docs/architecture/security-privacy.md).

## Reporting a vulnerability

Please report it privately with **Report a vulnerability** on the repository's
**Security** tab on GitHub (private vulnerability reporting), not in a public issue.
Include the version (Settings, About), the steps to reproduce and what you expected.
This is a student project, so there is no bounty and no response-time promise, but
reports are read and answered.

## Supported versions

Only the latest release on the GitHub Releases page gets fixes.

## External review, October 2026

An external code review reported 3 high, 6 medium and 22 low findings. Each was
reproduced first (a failing test where practical) and fixed in its own PR (#23 to #37).
Status as of PR #37:

| Finding | Status | Fix and regression test |
|---|---|---|
| H1 Electron 33 out of support | Fixed | Electron 45.0.0 (#24). `npm audit`: 10 (2 high) before, 8 moderate after; all 8 are in electron-builder's packaging tool chain (sprintf-js via @electron/get), none ships in the app |
| H2 Release build could not succeed, fuses never applied | Fixed | `.gitignore` anchored; `build/fuses.cjs` and icons committed; `fuses.cjs --check` step in release.yml (#25). Verified on a clean clone with an unpacked `--win --dir` build: all six hardening fuses set. Since `@electron/fuses` 2 all nine Electron 45 fuses are set explicitly and checked. `src/build-config.test.ts` |
| H3 Sidecar inherited the user's environment | Fixed | `sidecarEnv()` drops `ASCEND_*`, `NODE_OPTIONS`, `ELECTRON_RUN_AS_NODE` (and `PYTHON*` when packaged); the frozen sidecar ignores `ASCEND_TOKEN/HOST/DB_URL/DEV`, reads the token from stdin and binds 127.0.0.1 (#26). `electron/sidecar.test.ts`, `tests/unit/test_launch_env.py` |
| M1 A bad backup file broke the list and stopped daily backups | Fixed | #27, `tests/api/test_backup_robustness.py` |
| M2 Restore trusted any SQLite file at any path | Fixed | Backups folder only, no UNC, size cap, `integrity_check`, no triggers or views, safety copy only after the checks (#28). `tests/api/test_restore_trust.py` |
| M3 Production CSP allowed any localhost port | Fixed | `connect-src 'self'`; the dev server widens it only in dev (#29). `src/lib/csp.test.ts` |
| M4 `OLLAMA_HOST` without a scheme disabled the coach | Fixed | Normalised; loopback only unless `ASCEND_OLLAMA_ALLOW_REMOTE=1` (#30). `tests/unit/test_ollama_host.py` |
| M5 Export lost data | Fixed | Complete JSON export, re-importable CSV with cardio columns, local-date file names (#31). `tests/api/test_export_complete.py`, `src/lib/files.test.ts` |
| M6 Release and CI supply chain | Partly fixed | `contents: write` only on a tag-only publish job; every action pinned to a commit SHA; torch 2.14.1 (CVE-2025-32434) and `torch.load(weights_only=True)` (#32), `ml/tests/test_export.py`. **Open:** installers are unsigned (no certificate yet); `ml/requirements.txt` still uses `--extra-index-url` for the PyTorch CPU index (see below) |
| L1 Archived name reuse was a 500 | Fixed | #33, `tests/api/test_review_low.py` (also L2 to L7, L19) |
| L2 Negative workout duration after a clock change | Fixed | #33 |
| L3 Timezone-aware timestamps crashed or were stored 5h30 off | Fixed | #33 |
| L4 Huge ids were a 500 | Fixed | 422 for any number out of SQLite's range (#33) |
| L5 Wikipedia title not URL-encoded | Fixed | #33 |
| L6 Sets on archived exercises | Fixed | #33 |
| L7 Edits could null required fields | Fixed | #33 |
| L8 XP integrity | Fixed | Edits re-price XP (never upwards), corrections booked on the grant day, lost PRs lose their XP (#34). `tests/api/test_xp_integrity.py` |
| L9 Restart counter never reset | Fixed | 3 crashes per 10 minutes (#36). `electron/sidecar.test.ts` |
| L10 IPC requests had no timeout | Fixed | 30 s timeout; `/events` refused over IPC (#36) |
| L11 `export:save` payload unchecked | Fixed | `electron/ipc-validate.ts` (#36) |
| L12 Token sent to whoever owns the port | Fixed | `/health` returns an HMAC proof under the token; Electron checks it before sending the token (#36). `tests/api/test_health_proof.py`, `electron/sidecar.test.ts` |
| L13 Non-object Ollama replies were a 500 | Fixed | #30, `tests/unit/test_ollama_replies.py` |
| L14 Backups only in `%APPDATA%`, unencrypted | **Not fixed (deferred)** | Needs a "save backup elsewhere" flow and the planned optional encryption (security-privacy.md §7). Until then, copy `.ascendbak` files from Settings, Backups to another drive by hand |
| L15 CSV formula injection | Fixed | Text cells starting with `= + - @` (or tab/CR) get a leading `'` in exports; the importer strips it (#31), `tests/api/test_export_complete.py` |
| L16 Two quick starts made two active sessions | Fixed | Start is serialised in the sidecar (#35). `tests/api/test_review_runtime.py` (also L17, L20, L22) |
| L17 N x M XP queries, pagination skipped ties | Fixed | Two grouped queries per page; optional `before_id` keyset tie-break (#35) |
| L18 Pre-restore safety copies never pruned | Fixed | #28 |
| L19 Primary-muscle limit 4 vs 3 | Fixed | One constant, 4 (#33) |
| L20 `/shutdown` was TerminateProcess on Windows | Fixed | `/shutdown` sets uvicorn's `should_exit` (#35) |
| L21 27 React-hooks lint warnings | Partly fixed | Only the simple ones (#36): 27 to 25 warnings. The rest (refs read during render, effects that sync state) need component restructuring and stay as warnings |
| L22 Dev mode: static token with CORS for localhost:5173 | Fixed | No CORS at all; the Vite dev and preview servers proxy `/api` to the sidecar (#35). The dev token is still the fixed `dev`, which is fine without CORS |

### Known gaps and accepted risks

- **Unsigned installer.** Windows SmartScreen warns on first run. Code signing waits
  for a certificate; see security-privacy.md §6.
- **`--extra-index-url` in `ml/requirements.txt`.** It only affects the training
  machine and CI (the app ships ONNX Runtime alone). Every package is pinned to an exact
  version, and uv runs with `UV_INDEX_STRATEGY=unsafe-best-match`, which is needed
  because the PyTorch index also carries numpy, pillow and others. A hash-locked file
  (`uv pip compile --generate-hashes`) is the next step.
- **Not verified here:** the NSIS installer step and the publish job only run on the
  Windows runner and on a version tag. The unpacked Windows build and the fuse check were
  verified locally; the first tagged release should be watched end to end.
- **Local attackers** running as the same Windows user can read the database file
  directly; the sidecar's token and Host checks protect against other users' processes
  and web pages, not against your own account.
