# Security and Privacy

> Threat model, hardening rules and privacy commitments for ASCEND. Owner: Navin
> (review), implemented across lanes. ASCEND handles **health data and body photos** —
> the most sensitive data a consumer app can hold — so the default is: keep it on the PC.

---

## 1. Assets

| Asset | Sensitivity |
|---|---|
| Body metrics, measurements, injuries, pain logs | High (health data) |
| Progress photos | Very high |
| Meal photos, diet, chat history | Medium–high |
| Workout history | Medium |
| Sidecar launch token | High (local API access while running) |
| Release pipeline (GitHub tokens, future signing cert) | High (supply chain) |

## 2. Threat model (STRIDE, condensed)

| Threat | Example | Mitigation |
|---|---|---|
| **Spoofing** | Another local process or a web page calls the sidecar API | Random port, 32-byte token via stdin, `Host` header check (DNS rebinding), no CORS (also not in dev mode: Vite proxies `/api`), bind `127.0.0.1` only, inherited `ASCEND_*` variables ignored |
| | A process grabs the sidecar's port first and receives the token | `/health` returns an HMAC proof under the token; Electron sends the token only after the proof matches |
| **Tampering** | Malicious model file or update | SHA-256 verified downloads, atomic rename; updates only over HTTPS from GitHub Releases; ASAR integrity fuse; training checkpoints loaded with `torch.load(weights_only=True)` |
| | A crafted file restored as the database | Restore only from the backups folder, no UNC paths, size cap, `integrity_check`, no triggers or views, `trusted_schema` off |
| **Repudiation** | "I didn't change my plan" | Proposals table records who/when applied; local only |
| **Information disclosure** | Renderer XSS reads files | Sandbox, contextIsolation, no Node in renderer, strict CSP, no remote content, Markdown rendered without raw HTML |
| | Photos readable by other Windows users | Per-user install under `%APPDATA%`; optional AES-256-GCM (v1.1) |
| | Logs leak health data | Logging rules in [telemetry-model.md §2](telemetry-model.md#2-log-line-shape-sidecar) |
| **Denial of service** | Runaway LLM job freezes the app | Job timeouts, cancel, GPU lock, rules fallback |
| **Elevation of privilege** | `RunAsNode` abuse of the signed app | Electron fuses: `RunAsNode` off, `EnableNodeOptionsEnvironmentVariable` off, `OnlyLoadAppFromAsar` on |

## 3. Electron hardening checklist

Checked against the code in October 2026 (external review, see [SECURITY.md](../../SECURITY.md)).

- [x] `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` (`webSecurity`
  left at its default, true)
- [x] Production CSP `connect-src 'self'`: the renderer reaches the sidecar only through
  IPC; the dev server widens it for Vite alone (`src/lib/csp.ts`)
- [x] `will-navigate` blocked; `setWindowOpenHandler` denies all, `https://` links open
  in the system browser
- [x] IPC allow-list with hand-written shape checks in main (method, path,
  `export:save` payload in `electron/ipc-validate.ts`); no `remote` module. Not zod.
- [x] Fuses set at build time by `apps/desktop/build/fuses.cjs` (afterPack) and checked
  in release.yml with `fuses.cjs --check`: RunAsNode, NODE_OPTIONS and CLI inspect off,
  cookie encryption, embedded ASAR integrity and OnlyLoadAppFromAsar on. All nine of
  Electron 45's fuses are set explicitly (`@electron/fuses` 2, `strictlyRequireAllFuses`),
  so an Electron upgrade that adds a fuse fails the build until it is decided.
- [x] `app.requestSingleInstanceLock()`
- [x] Electron within the supported versions (45.0.0); Dependabot security alerts on,
  no version-update PRs (upgrades are done by hand in tested commits)
- [x] The sidecar gets a cleaned environment and its token on stdin; requests from the
  renderer time out after 30 s

### 3a. One action allowlist (v1.1)

Nothing typed into the app, and nothing a local model writes, can run an arbitrary operation.
[`packages/shared/src/command-vectors.json`](../../packages/shared/src/command-vectors.json)
lists the only data-changing actions (`actions`: log a set, a hold, a weigh-in or food,
switch program, erase data) with their risk, the command bar's local UI commands (`ui`)
and what a trainer reply may ask the UI to do (`chat_ui`). The sidecar's actions registry
runs exactly that list, each one only after Confirm (erase also needs the word typed), with
an audit log and Undo where possible. Tests on both sides read the same file:
`tests/unit/test_action_allowlist.py` (registry, parser, chat reply kinds) and
`apps/desktop/src/lib/allowlist.test.ts` (command bar). `share:open` in the Electron main
process has its own allowlist: X's post composer only (§3).

## 4. Privacy commitments

1. **No account, no cloud, no telemetry.** Data lives in `%APPDATA%\ASCEND`.
2. **Network egress is limited** to: model downloads (opt-in, per model), update check
   (can be disabled), and the wger.de exercise lookup. That lookup is off by default, is enabled
   only behind a consent dialog in Settings, and is asked again per exercise in "Add your own
   exercise". It runs from the sidecar and sends only the exercise name (ADR-0013). A CI test runs the packaged app's E2E journey with outbound
   network blocked except `127.0.0.1` and fails on any other connection attempt.
3. **EXIF stripped** from every photo on import (location, device): built in v1.1, see
   [photos-and-sharing.md](photos-and-sharing.md). Optional AI photo feedback is off by default,
   never runs for under-18s and never estimates body fat or weight.
4. **Delete everything:** typed confirmation, then the database, photos, backups and
   logs are wiped.
5. **Export everything:** CSV/JSON/`.ascendbak` at any time ([ADR-0010](adr/0010-import-export-formats.md)).
6. **Training data consent:** corrections leave a PC only when the user exports them;
   team photos used for testing are collected with consent. What each model sees, the
   consent flow and AI-specific deletion: [docs/ai/data-and-privacy-for-ai.md](../ai/data-and-privacy-for-ai.md).

## 5. India's DPDP Act — notes, not legal advice

- The Digital Personal Data Protection Act 2023 and DPDP Rules 2025 (notified Nov 2025,
  phased; substantive duties around May 2027 per law-firm summaries — **verify before
  any public release**) apply to *data fiduciaries* processing personal data.
- ASCEND as designed collects nothing: the team never receives users' data, so most
  fiduciary duties don't arise. If that changes (crash upload, sync, a website signup),
  an ADR and a privacy review are mandatory first.
- Consent screens are still shown at onboarding (what is stored, where, how to delete),
  because it is the right UX for health data.

## 6. Supply chain

| Control | Status |
|---|---|
| gitleaks | Pre-commit hook (`.pre-commit-config.yaml`); not in CI yet |
| `npm audit`, `pip-audit` in CI | Not in CI yet; run by hand for releases (October 2026: 8 moderate, all in electron-builder's packaging tool chain) |
| CycloneDX SBOM per release | Not yet |
| SHA-256 checksums for models | Model manifest (`models-manifest.json`) |
| GitHub Actions pinned by commit SHA | Done, version in a comment; bump both by hand |
| Least-privilege workflow token | Read-only everywhere; `contents: write` only on the tag-only publish job in release.yml |
| Electron fuses verified on every release build | Done (`fuses.cjs --check`) |
| ML dependencies | Exact pins; torch 2.14.1. `--extra-index-url` for the PyTorch CPU index remains (training machine and CI only); hash-locking is the next step |
| Dependabot | Security alerts and security updates on (repo settings); no version-update config, upgrades are done by hand |
| Code signing | Unsigned until decided; Azure Artifact Signing (Basic $9.99/month per Microsoft's pricing page) — **eligibility for an individual in India unverified** |

## 7. Optional encryption (planned; not in v1.1.0)

SQLCipher for the database and AES-256-GCM for photos. The key lives in Windows DPAPI
via Electron `safeStorage` and reaches the sidecar over stdin at launch. A printed
recovery code is the only way back if the Windows profile is lost — the UI says so
plainly before the user turns it on.

## 8. Safety (health)

- ASCEND is **not a medical device**; shown at onboarding and in every injury protocol.
- Red-flag symptoms (sharp pain, chest pain, numbness, dizziness, fainting, pain ≥ 7)
  bypass the model and return a fixed "stop and see a doctor or physio" reply. Full safety
  rules, word lists and post-checks: [docs/ai/coach-llm.md §6](../ai/coach-llm.md#6-medical-safety-rules).
- Diet advice never goes under 1,500 kcal (men) / 1,200 kcal (women) without a warning
  (common guideline; estimate).
