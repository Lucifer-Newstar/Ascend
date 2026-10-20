# Component Diagram — Runtime Components and Interfaces

> **Diagram 5 (UML 2.5 — Structural).** Components with their provided (`●`) and
> required (`○`) interfaces. Matches [system-architecture.md §3](../system-architecture.md#3-processes).

```mermaid
flowchart LR
    subgraph E["«process» ASCEND.exe"]
        UI["«component»<br/>Renderer UI"]
        BR["«component»<br/>Preload bridge<br/>● window.ascend"]
        SUP["«component»<br/>Sidecar supervisor"]
        ROUTER["«component»<br/>IPC router<br/>(allow-list + zod)"]
        UPD["«component»<br/>Updater"]
        NOTIF["«component»<br/>Notifications + tray"]
    end
    subgraph S["«process» ascend-sidecar.exe"]
        API["«component»<br/>REST + SSE API<br/>● REST + SSE"]
        DOM["«component»<br/>Domain modules"]
        BUS["«component»<br/>Event bus + outbox"]
        JOBS["«component»<br/>Job queue"]
        MM["«component»<br/>Model manager"]
        CLS["«component»<br/>Food classifier<br/>(ONNX, CPU)"]
    end
    OLL["«external»<br/>Ollama<br/>● /api/chat, /api/generate"]
    DB[("«datastore»<br/>SQLite")]
    GH["«external»<br/>GitHub Releases"]

    UI -- "○ window.ascend" --> BR
    BR -- "ipc invoke" --> ROUTER
    ROUTER -- "○ REST (HTTP + token)" --> API
    SUP -- "spawn, ○ /health" --> API
    API --> DOM
    DOM --> BUS
    DOM --> JOBS
    JOBS --> MM
    MM -- "○ Ollama API" --> OLL
    MM --> CLS
    DOM --> DB
    BUS --> DB
    JOBS --> DB
    UPD -- "○ latest.yml" --> GH
    ROUTER --> NOTIF
```

| Interface | Provided by | Contract |
|---|---|---|
| `window.ascend` | Preload | [ipc-contract.md](../../contracts/ipc-contract.md) |
| REST paths + SSE | Sidecar API | [contracts/](../../contracts/README.md) |
| `/health`, `/shutdown` | Sidecar API | [system.yaml](../../contracts/system.yaml) |
| Ollama API | Ollama | Ollama docs (external) |
