# Package Diagram — Repository and Sidecar Modules

> **Diagram 4 (UML 2.5 — Structural).** How the code is packaged and which packages may
> depend on which. Arrows are `<<import>>` dependencies. Rules are enforced by
> `import-linter` (Python) and ESLint `no-restricted-imports` (TypeScript).

```mermaid
flowchart TB
    subgraph desktop["apps/desktop"]
        main["main"]
        preload["preload"]
        renderer["renderer"]
        shared["shared<br/>(api-types.gen, ipc types)"]
        renderer --> shared
        preload --> shared
        main --> shared
    end
    subgraph sidecar["services/sidecar/app"]
        subgraph modules["modules"]
            workouts
            nutrition
            gamification
            coach
            progress
            io
        end
        core["core<br/>(db, events, jobs, security, logging)"]
        ai["ai<br/>(model_manager, ollama_client, onnx_runtime, fallbacks)"]
        modules --> core
        nutrition --> ai
        coach --> ai
        ai --> core
    end
    subgraph ml["ml"]
        mlsrc["src (prepare, train, export, evaluate)"]
    end
    contracts["docs/contracts<br/>(OpenAPI + IPC)"]
    shared -. generated from .-> contracts
    sidecar -. implements .-> contracts
    ai -. loads artefact from .-> mlsrc
```

## Dependency rules

| Rule | Enforced by |
|---|---|
| `renderer` imports nothing from `main` or Node built-ins | ESLint + Vite renderer config |
| `modules.*` never import another module's `repo` or `models` — only its `service` or events | import-linter `independence` + `layers` contracts |
| `core` imports no module | import-linter `layers` |
| `ai` imports `core` only | import-linter |
| `ml` is never imported by the sidecar; only its exported ONNX file + `labels.json` cross over | Packaging (`ml/` excluded from PyInstaller) |
