# State Machine Diagram — Sidecar Supervisor

> **Diagram 10 (UML 2.5 — Behavioural).** The supervisor in Electron main
> (`apps/desktop/electron/sidecar.ts`) that owns the sidecar process. The five states are
> the `SidecarState` values in `packages/shared/src/ipc.ts`; the renderer reads them with
> `sidecarStatus()` and, from Phase 0, receives them on `sidecar:state-changed`.
> Guards show the **v1.0 target**; v0.1 differences are in
> [system-architecture.md §5](../system-architecture.md#5-sidecar-lifecycle).

```mermaid
stateDiagram-v2
    [*] --> stopped
    stopped --> starting : app ready / start()
    starting --> ready : GET /health 200
    starting --> restarting : not healthy before timeout
    ready --> restarting : process exited unexpectedly / 3 missed health checks
    restarting --> starting : backoff elapsed (1, 2, 4, 8, 16 s)
    restarting --> failed : restart limit reached
    failed --> starting : user clicks "Restart engine"
    ready --> stopped : app quit / POST /shutdown, kill after grace
    restarting --> stopped : app quit
    failed --> stopped : app quit
    stopped --> [*]

    note right of failed
        Error screen: what failed,
        "your data is safe", Restart engine,
        Open logs
    end note
```

| State | Renderer shows | `request()` behaviour |
|---|---|---|
| `starting` | Splash "Starting engine…" | rejects (`sidecar is starting`) |
| `ready` | App | forwarded with token |
| `restarting` | Banner "Reconnecting…", unsaved rows kept | rejects; UI retries after `ready` |
| `failed` | Error screen | rejects |
| `stopped` | — (app quitting) | rejects |

## Second machine: a background job (Phase 2)

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running : worker free (GPU lock for model jobs)
    running --> succeeded : result saved
    running --> retrying : error and attempts < 3
    retrying --> queued : backoff elapsed
    running --> timed_out : timeout (scan 60 s, review 120 s)
    running --> cancelled : user cancels
    retrying --> failed : attempts = 3
    timed_out --> [*]
    succeeded --> [*]
    cancelled --> [*]
    failed --> [*]
```
