# Telemetry Model — Local Only

> What ASCEND records about its own behaviour, in what shape, and where it stays.
> **Nothing in this document is ever sent off the PC.** There is no analytics SDK, no
> crash upload, no "anonymous usage statistics". Owner: Gokul (pipelines + dev
> dashboards) with Jegatheesan (sidecar logging) and Dhanush (Electron logging).

---

## 1. Signals

| Signal | Producer | Format | Location | Retention |
|---|---|---|---|---|
| Sidecar logs | structlog | JSON lines | `%APPDATA%\ASCEND\logs\sidecar.log` | Rotate 10 MB × 5 |
| Main + renderer logs | electron-log | text lines with JSON fields | `logs\main.log`, `logs\renderer.log` | Rotate 10 MB × 5 |
| Domain events | sidecar event bus | Pydantic event envelope (§3) | `events_outbox` table | Pruned after dispatch + 30 days |
| Job records | job queue | `jobs` table | SQLite | 30 days |
| Model performance | model manager | tokens/s, first-token ms, VRAM peak | `models_installed`, logs | Latest + history 30 days |
| Crash dumps | Electron `crashReporter` (`uploadToServer: false`) | minidump | `crashes\` | Last 10 |
| Sidecar crashes | `faulthandler` + `sys.excepthook` | `crash-<ts>.txt` | `crashes\` | Last 10 |
| UI errors | React error boundaries | log line + boundary id | `renderer.log` | with logs |
| Dev metrics | `prometheus_client` behind `ASCEND_DEV_METRICS=1` | Prometheus text | `GET /metrics` on the sidecar | Dev only, never in release builds |

## 2. Log line shape (sidecar)

```json
{
  "ts": "2026-11-20T14:03:11.482Z",
  "level": "info",
  "logger": "workouts.service",
  "event": "set_completed",
  "corr_id": "c-7f3a9e",
  "session_id": 412,
  "duration_ms": 6.1,
  "algo_version": "load-1.0.0"
}
```

Rules: `event` is snake_case; **no free text from the user** (meal names, chat
messages, notes) and **no body data** (weight, measurements) in logs; ids only.
`corr_id` is created by main per request and passed in `X-Correlation-Id`, so one id
follows renderer → main → sidecar → job.

## 3. Domain event envelope

```json
{
  "event_id": "01JCE6H2T8Q4…",
  "type": "SetLogged",
  "version": 1,
  "occurred_at": "2026-11-20T14:03:11.470Z",
  "corr_id": "c-7f3a9e",
  "payload": { "set_id": 9921, "session_id": 412, "exercise_id": 17 }
}
```

- `event_id` is a ULID (sortable). `version` bumps on any payload change (additive
  fields do not bump).
- Event types: see [system-architecture.md §8](system-architecture.md#8-event-bus-transactional-outbox).
- Renderer receives a filtered subset over SSE (`dashboard.changed`, `job.progress`,
  `pr.achieved`, `level.up`, `quest.completed`, `chat.token`).

## 4. Dev-time metrics (Prometheus, opt-in)

| Metric | Type | Labels |
|---|---|---|
| `ascend_http_request_duration_seconds` | histogram | route, method, status |
| `ascend_job_duration_seconds` | histogram | type, status |
| `ascend_job_queue_depth` | gauge | worker |
| `ascend_llm_first_token_seconds` | histogram | model |
| `ascend_llm_tokens_per_second` | gauge | model |
| `ascend_scan_items_total` | counter | outcome (`preselected`/`chips`/`question`/`fallback`) |
| `ascend_event_handler_seconds` | histogram | handler |

Grafana dashboard JSON in `infra/compose/grafana/` (Gokul). Prometheus scrapes the dev
sidecar on a fixed dev port ([port-register.md](port-register.md)). Release builds do not
contain the `/metrics` route.

## 5. Diagnostics bundle

Settings → Diagnostics → "Export bundle" creates a zip the **user** can attach to a
GitHub issue themselves:

| Included | Scrubbed / excluded |
|---|---|
| App, sidecar, Ollama, model versions; OS build; GPU name + VRAM | User name in paths replaced by `<user>` |
| Last 2 log files of each kind | Lines with `level=debug`; any field not on the allow-list |
| Crash files | Database, photos, chat text, food names, body metrics — never included |
| Health snapshot (`/health` JSON), job failures (type + error code) | Tokens, keys, file paths outside `%APPDATA%\ASCEND` |

## 6. What is measured for evaluation

Evaluation runs ([evaluation.md](../operations/evaluation.md)) read local logs and
dev metrics on the team's own machines. Crash-free session rate is computed from the
local session journal (`app_meta.sessions`: start, clean exit yes/no) — on testers'
machines only, shared by them manually.
