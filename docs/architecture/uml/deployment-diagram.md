# Deployment Diagram — User PC and Release Pipeline

> **Diagram 7 (UML 2.5 — Structural).** Where artefacts run. The left side is the only
> runtime environment; the right side is how artefacts are built and delivered.

```mermaid
flowchart LR
    subgraph PC["«device» User PC — Windows 11 (reference: Ryzen 7 7435HS, 12 GB RAM, RTX 3050 Laptop 4 GB)"]
        subgraph EE["«execution environment» Electron runtime"]
            A1["«artifact» ASCEND.exe + app.asar"]
        end
        subgraph PY["«execution environment» PyInstaller bundle (Python 3.12)"]
            A2["«artifact» ascend-sidecar.exe (one-folder)"]
            A3["«artifact» ascend-food-cls.onnx"]
        end
        subgraph OL["«execution environment» Ollama service"]
            A4["«artifact» qwen3:4b"]
            A5["«artifact» qwen3-vl:2b"]
        end
        subgraph FS["«storage» %APPDATA%/ASCEND"]
            A6["«artifact» ascend.db (WAL)"]
            A7["«artifact» photos/ backups/ logs/"]
        end
        GPU["«device» GPU (CUDA)"]
    end
    subgraph CI["«execution environment» GitHub Actions (windows-latest, ubuntu-latest)"]
        B1["build sidecar → build installer → smoke test"]
    end
    subgraph REL["«node» GitHub Releases"]
        R1["«artifact» ASCEND-Setup-x.y.z.exe"]
        R2["«artifact» latest.yml + blockmap"]
        R3["«artifact» SHA256SUMS, sbom.cdx.json"]
        R4["«artifact» models-manifest.json"]
    end

    A1 -- "HTTP 127.0.0.1:random" --> A2
    A2 -- "HTTP 127.0.0.1:11434" --> OL
    OL --> GPU
    A2 --> FS
    B1 --> REL
    A1 -. "HTTPS update check (opt-in)" .-> R2
    A2 -. "HTTPS model manifest (opt-in)" .-> R4
```
