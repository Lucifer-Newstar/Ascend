# Port and IPC Register

> Every localhost port and every Electron IPC channel ASCEND uses, in one place.
> **Rule:** a new port or channel gets a row here in the same PR that introduces it.
> Owner: Navin (register), Dhanush (IPC), Gokul (dev infrastructure).

---

## 1. Runtime ports (shipped app)

| Component | Bind | Port | Protocol | Auth | Notes |
|---|---|---|---|---|---|
| Sidecar API | `127.0.0.1` | **random** (main binds `:0`, passes it in `ASCEND_PORT`) | HTTP/1.1 (+ SSE from Phase 1) | Bearer launch token + `Host` check | Never fixed in release builds; never `0.0.0.0`. Prints `ASCEND_SIDECAR_READY port=<n>` when up |
| Ollama | `127.0.0.1` | **11434** (Ollama's default) | HTTP | none (local) | Installed by the user; `OLLAMA_HOST` respected if set |
| Electron renderer | — | none | `app://` custom protocol / `file://` | — | No dev server in release builds |

The release app opens **no listening port** other than the sidecar's random one.

## 2. Development ports (team machines only)

| Component | Bind | Port | Started by | Notes |
|---|---|---|---|---|
| Vite dev server (renderer) | `127.0.0.1` | 5173 | `npm run dev` | HMR |
| Sidecar (dev, fixed) | `127.0.0.1` | 8765 | `uv run python -m app --dev` in `services/sidecar` | Fixed port only with `--dev`; token `dev`; CORS for the Vite origin |
| Prism mock server | `127.0.0.1` | 4010 | `npm run mock` | Serves `docs/contracts/*.yaml` examples |
| MLflow tracking UI | `127.0.0.1` | 5000 | `docker compose -f infra/compose/mlflow.yml up` | Artefacts in a local volume |
| Prometheus | `127.0.0.1` | 9090 | `infra/compose/observability.yml` | Scrapes `host.docker.internal:8765/metrics` |
| Grafana | `127.0.0.1` | 3000 | `infra/compose/observability.yml` | Dashboard JSON in repo |
| Electron remote debugging | `127.0.0.1` | 9222 | `npm run dev:electron -- --inspect` | Dev only; Playwright attaches here |

Collisions: 3000 and 5000 are common on Windows dev machines; override with
`GRAFANA_PORT` / `MLFLOW_PORT` in `infra/compose/.env` and note it here.

## 3. Environment variables (sidecar)

Read in `services/sidecar/app/core/config.py`.

| Variable | Set by | Default | Meaning |
|---|---|---|---|
| `ASCEND_PORT` | main | `8765` | Port to listen on (main always sets a random one) |
| `ASCEND_DATA_DIR` | main | `%APPDATA%\ASCEND` (`~/.ascend` elsewhere) | Database, photos, logs |
| `ASCEND_DB_URL` | tests | derived from data dir | Override the SQLite URL |
| `ASCEND_HOST` | — | `127.0.0.1` | Bind host for `python -m app` (the dev container uses `0.0.0.0`); the packaged sidecar ignores it and always binds `127.0.0.1` |
| `ASCEND_DEV` | `--dev` flag | unset | `1` enables dev CORS |
| `ASCEND_COACH_MODEL` | settings | `qwen3:4b` | Ollama model for the coach |
| `OLLAMA_HOST` | user / settings | `http://127.0.0.1:11434` | Ollama address, in Ollama's own format too (`127.0.0.1:11434`, `0.0.0.0`, `localhost`; no scheme = http, port 11434). A host that is not on this PC turns the coach off unless `ASCEND_OLLAMA_ALLOW_REMOTE=1` |
| `ASCEND_OLLAMA_ALLOW_REMOTE` | user | unset | `1` allows a non-loopback `OLLAMA_HOST` (the coach then sends health facts to it over plain HTTP) |
| `ASCEND_DEV_METRICS` | dev only | unset | `1` enables `/metrics` (Phase 2) |
| *(token)* | main → **stdin** | — | First line on stdin; the sidecar keeps it in process memory. `--dev` uses `dev` |

Electron main does not pass its own environment through untouched (`sidecarEnv` in
`electron/sidecar.ts`): every inherited `ASCEND_*` variable except `ASCEND_COACH_MODEL` and
`ASCEND_OLLAMA_ALLOW_REMOTE` is dropped, as are `NODE_OPTIONS` and `ELECTRON_RUN_AS_NODE` (and `PYTHON*` in the
packaged app); it then sets `ASCEND_PORT` and `ASCEND_DATA_DIR`. The packaged sidecar also
ignores `ASCEND_TOKEN`, `ASCEND_HOST`, `ASCEND_DB_URL` and `ASCEND_DEV` and refuses
`--dev`, so a leftover `ASCEND_TOKEN=dev` or `ASCEND_HOST=0.0.0.0` can't weaken the app.

## 4. IPC channels (renderer ↔ main)

Full payloads, errors and examples: [contracts/ipc-contract.md](../contracts/ipc-contract.md).
Channel names live in the `IPC` constant in `packages/shared/src/ipc.ts`.

| Channel | Direction | Kind | Purpose | Status |
|---|---|---|---|---|
| `sidecar:request` | R → M | invoke | Proxy a REST call to the sidecar (method, path, body); main adds the token | v0.1 |
| `sidecar:status` | R → M | invoke | Supervisor state, port, restarts, last error | v0.1 |
| `export:save` | R → M | invoke | Native save dialog + write export content | v0.1 |
| `app:info` | R → M | invoke | App version, platform, Electron version | v0.1 |
| `sidecar:state-changed` | M → R | push | Supervisor state transitions | Phase 0 |
| `sidecar:restart` | R → M | invoke | User-triggered "Restart engine" | Phase 0 |
| `events:subscribe` / `events:unsubscribe` | R → M | invoke | Start/stop receiving sidecar SSE events | Phase 1 |
| `events:push` | M → R | push | One sidecar event delivered to the renderer | Phase 1 |
| `notify:show` | R → M | invoke | Windows toast | Phase 1 |
| `notify:schedule` | R → M | invoke | Schedule a reminder (tray must be running) | Phase 1 |
| `files:pick-image` | R → M | invoke | Native dialog for a meal/progress photo | Phase 2 |
| `files:pick-import` | R → M | invoke | Native dialog for CSV / `.ascendbak` | Phase 3 |
| `app:open-path` | R → M | invoke | Open logs/data folder in Explorer (allow-listed targets) | Phase 3 |
| `update:check` | R → M | invoke | Check for an update now | Phase 3 |
| `update:status` | M → R | push | Update available / downloading / ready | Phase 3 |
| `update:install` | R → M | invoke | Quit and install | Phase 3 |
| `window:titlebar-theme` | R → M | invoke | Match title-bar overlay colours to the theme | Phase 4 |
| `secure:get-key` | main only | internal | safeStorage key for encryption (never exposed) | v1.1 |

## 5. SSE event names (sidecar → main → renderer)

| Event | Payload (summary) |
|---|---|
| `dashboard.changed` | which tiles to refresh |
| `job.progress` | job_id, type, progress 0–1, status |
| `chat.token` | thread_id, message_id, token |
| `chat.done` | thread_id, message_id, used_data |
| `pr.achieved` | exercise_id, type, value |
| `level.up` | level, rank |
| `quest.completed` | quest_id, item_id, xp |
| `model.status` | name, state (`missing`/`downloading`/`ready`/`error`), progress |
