# Composite Structure Diagram — Inside the Sidecar

> **Diagram 6 (UML 2.5 — Structural).** The internal parts of the `Sidecar` composite,
> its ports, and the connectors between parts. Mermaid has no composite-structure
> notation; ports are drawn as small round nodes on the boundary.

```mermaid
flowchart LR
    pHTTP(("pHTTP<br/>:random"))
    pSTDIN(("pStdin<br/>token"))
    pOLL(("pOllama"))
    pFS(("pFiles"))
    subgraph Sidecar["Sidecar : composite"]
        api["api : FastAPIApp"]
        sec["guard : TokenGuard"]
        svc["services[6] : ModuleService"]
        bus["bus : EventDispatcher"]
        q["queue : JobQueue"]
        gw["gpuWorker : Worker [1]"]
        cw["cpuWorker : Worker [1]"]
        mm["models : ModelManager"]
        db["db : SqliteEngine"]
    end
    pHTTP --- sec --- api
    pSTDIN --- sec
    api --- svc
    svc --- db
    svc --- bus
    bus --- db
    svc --- q
    q --- gw
    q --- cw
    gw --- mm
    cw --- mm
    mm --- pOLL
    db --- pFS
```

| Part | Multiplicity | Note |
|---|---|---|
| `services` | 6 | workouts, nutrition, gamification, coach, progress, io |
| `gpuWorker` | exactly 1 | 4 GB VRAM holds one model at a time |
| `cpuWorker` | exactly 1 | classifier, exports, backups |
| `guard` | 1 | checks Bearer token and `Host` on every request |
