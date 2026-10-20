# Integration Edge Cases — Cross-Member Risk Register

> Where two lanes meet, things break. This register lists the known seams, what can go
> wrong, and who guards each. Maintainer: Team Lead. Review at every phase gate.
> Severity: **H** = blocks a release · **M** = user-visible bug · **L** = annoyance.
> AI-specific risks (hallucinated numbers, unsafe advice, VRAM, licences, Tamil quality) have
> their own register: [docs/ai/ai-risks.md](../ai/ai-risks.md).

---

## 1. Process and IPC seams (frontend ↔ backend ↔ DevOps)

| # | Edge case | Sev | Guard | Owner |
|---|---|---|---|---|
| E1 | Sidecar picks a port that another app grabs between bind and listen | M | Main binds `127.0.0.1:0`, passes the port; sidecar retries once on `EADDRINUSE` and main re-spawns with a new port | Dhanush |
| E2 | Antivirus quarantines `ascend-sidecar.exe` (PyInstaller false positive) | H | One-folder build (not one-file); error screen names the file and shows "Restore and allow"; checksum published | Gokul |
| E3 | Sidecar slow to start on first run (cold disk, Defender scan) | M | Ready timeout 20 s with splash "Starting engine…"; second attempt at 40 s before error | Dhanush |
| E4 | Renderer calls an IPC channel not in the allow-list | M | Main rejects with `IPC_CHANNEL_DENIED`; dev build throws loudly; contract test lists every channel | Dhanush |
| E5 | OpenAPI implementation drifts from `docs/contracts` | H | CI drift job compares FastAPI's emitted OpenAPI per tag with the contract file | Gokul / Jegatheesan |
| E6 | Two windows/instances open the same DB | H | `app.requestSingleInstanceLock()`; second launch focuses the first | Dhanush |
| E7 | App closed mid-write | H | WAL + transactional outbox; on start, replay undelivered events; `/shutdown` checkpoints WAL | Jegatheesan |
| E8 | Windows user name with non-ASCII characters (Tamil, spaces) in `%APPDATA%` path | M | All paths via `pathlib`/`path.join`; CI test with a Unicode temp dir | Gokul |
| E9 | SSE connection drops (sleep/hibernate) | M | Renderer reconnects with `Last-Event-ID`; server keeps a 500-event ring buffer | Jegatheesan / Dhanush |

## 2. Data and engine seams

| # | Edge case | Sev | Guard | Owner |
|---|---|---|---|---|
| E10 | Editing a past set must re-run PR, XP, muscle load and quests | M | Edits emit `SetUpdated`; projectors are idempotent and recompute by date range | Jegatheesan |
| E11 | Day boundary: quest reset at 4 AM vs calendar day for rings | M | One `day_key(ts, reset_hour)` helper used by every module; tests at 03:59/04:00 | Jegatheesan |
| E12 | Units kg/lb and cm/in mixed in history after a settings change | M | Store SI only; convert at the edge; import adapters convert on ingest | Jegatheesan |
| E13 | Formula change makes old numbers differ | M | Every derived row stores `algo_version`; a migration replays history; changelog explains | Navin / Jegatheesan |
| E14 | Duplicate set from double-click / key repeat | L | Merge duplicates within 60 s (same exercise, weight, reps) | Jegatheesan |
| E15 | Implausible values (typo 700 kg) inflate PR/XP | M | >10% e1RM jump asks to confirm; >15% needs confirmation for rank; no XP past 3 h/session | Jegatheesan |
| E16 | Migration fails on a user's DB | H | Auto-backup before migrating; restore + show error on failure; CI upgrades fixture DBs from every released schema | Jegatheesan / Gokul |
| E17 | Strong changed its CSV format (Oct 2025) | M | Adapter detects header variant; golden fixtures for both | Jegatheesan / Gokul |

## 3. AI and ML seams

| # | Edge case | Sev | Guard | Owner |
|---|---|---|---|---|
| E18 | Chat model and VLM both need the GPU (4 GB can't hold both) | H | Job queue GPU lock; unload chat (`keep_alive: 0`) before a VLM second-opinion job, reload after; classifier on CPU, so the default scan never needs the GPU | Jegatheesan |
| E19 | Ollama not installed / not running / old version | M | Detect at onboarding; try to start; else rules mode + banner; min version in manifest | Jegatheesan |
| E20 | Model download interrupted or tampered | M | Resumable download, SHA-256 verify, atomic rename | Jegatheesan |
| E21 | Classifier labels don't match the food DB ids | H | `labels.json` maps class → INDB/IFCT id; CI checks every label resolves | Navin |
| E22 | Preprocessing differs between training and the app (resize, normalise) | H | One preprocessing contract (doc + test vector); ONNX parity test on 200 images | Navin / Jegatheesan |
| E23 | LLM invents numbers in the weekly review | H | Prompt gets the numbers; output is checked: any number not in the input → fall back to template | Jegatheesan |
| E24 | Red-flag symptom typed in Tamil or mixed script | H | Red-flag list in English, Tamil and transliterated forms; tested; bypasses model | Jegatheesan / Navin |
| E25 | User's own photos leak into training | M | Confirmed user photos are the test set only, tagged in DVC; training script refuses that tag | Navin |
| E26 | Low-VRAM teammate can't run AI features | L | Rules mode + CPU tier (qwen3:1.7b); AI tests marked and skippable | Navin |

## 4. Release seams

| # | Edge case | Sev | Guard | Owner |
|---|---|---|---|---|
| E27 | Auto-update installs a build with a newer DB schema, user downgrades | H | Downgrade not supported; app refuses to open a newer schema and offers restore from backup | Gokul / Jegatheesan |
| E28 | SmartScreen warning on unsigned installer | M | Documented in release notes; checksums published; signing options tracked | Gokul / Navin |
| E29 | Release asset uploaded but `latest.yml` missing → updater fails | H | Release workflow verifies assets before publishing the draft | Gokul |
| E30 | Model-only update incompatible with app version | M | Manifest field `min_app_version`; app ignores incompatible models | Navin |
