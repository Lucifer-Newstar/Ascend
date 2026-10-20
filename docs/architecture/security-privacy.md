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
| **Spoofing** | Another local process or a web page calls the sidecar API | Random port, 32-byte token via stdin, `Host` header check (DNS rebinding), CORS off, bind `127.0.0.1` only |
| **Tampering** | Malicious model file or update | SHA-256 verified downloads, atomic rename; updates only over HTTPS from GitHub Releases; ASAR integrity fuse |
| **Repudiation** | "I didn't change my plan" | Proposals table records who/when applied; local only |
| **Information disclosure** | Renderer XSS reads files | Sandbox, contextIsolation, no Node in renderer, strict CSP, no remote content, Markdown rendered without raw HTML |
| | Photos readable by other Windows users | Per-user install under `%APPDATA%`; optional AES-256-GCM (v1.1) |
| | Logs leak health data | Logging rules in [telemetry-model.md §2](telemetry-model.md#2-log-line-shape-sidecar) |
| **Denial of service** | Runaway LLM job freezes the app | Job timeouts, cancel, GPU lock, rules fallback |
| **Elevation of privilege** | `RunAsNode` abuse of the signed app | Electron fuses: `RunAsNode` off, `EnableNodeOptionsEnvironmentVariable` off, `OnlyLoadAppFromAsar` on |

## 3. Electron hardening checklist

- [ ] `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, `webSecurity: true`
- [ ] CSP: `default-src 'self'; img-src 'self' data: blob:; connect-src 'self'` (renderer never talks to the network)
- [ ] `will-navigate` and `setWindowOpenHandler` deny everything
- [ ] IPC allow-list + zod validation in main; no `remote` module
- [ ] Fuses set at build time (Gokul, `build/fuses.js`)
- [ ] `app.requestSingleInstanceLock()`
- [ ] Electron kept within the supported versions; Dependabot on

## 4. Privacy commitments

1. **No account, no cloud, no telemetry.** Data lives in `%APPDATA%\ASCEND`.
2. **Network egress is limited** to: model downloads (opt-in, per model), update check
   (can be disabled). A CI test runs the packaged app's E2E journey with outbound
   network blocked except `127.0.0.1` and fails on any other connection attempt.
3. **EXIF stripped** from every photo on import (location, device).
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

| Control | Where |
|---|---|
| `npm audit` / `npm audit`, `pip-audit` | CI on every PR |
| gitleaks (pre-commit + CI) | No secrets in git |
| CycloneDX SBOM per release | Release assets |
| SHA-256 checksums for installer and models | Release assets + model manifest |
| Pinned GitHub Actions by commit SHA | Workflows |
| Dependabot weekly | Repo settings |
| Code signing | Unsigned until decided; Azure Artifact Signing (Basic $9.99/month per Microsoft's pricing page) — **eligibility for an individual in India unverified** |

## 7. Optional encryption (v1.1)

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
