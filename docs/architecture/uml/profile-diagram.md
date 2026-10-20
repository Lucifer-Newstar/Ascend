# Profile Diagram — ASCEND UML Stereotypes

> **Diagram 8 (UML 2.5 — Structural).** The stereotypes used in this UML set, the UML
> metaclass each extends, and their tagged values. Only these stereotypes appear in
> diagrams 1–14.

```mermaid
classDiagram
    direction LR
    class Component {
        <<metaclass>>
    }
    class Class {
        <<metaclass>>
    }
    class Node {
        <<metaclass>>
    }
    class Artifact {
        <<metaclass>>
    }
    class Actor {
        <<metaclass>>
    }
    class process {
        <<stereotype>>
        +str runtime
        +str owner
    }
    class service {
        <<stereotype>>
        +str algo_version
        +bool deterministic
    }
    class datastore {
        <<stereotype>>
        +str engine
        +str journal_mode
    }
    class external {
        <<stereotype>>
        +str bind
        +bool optional
    }
    class artifact {
        <<stereotype>>
        +str version
        +str sha256
    }
    class device {
        <<stereotype>>
        +int ram_gb
        +int vram_gb
    }
    class system {
        <<stereotype>>
        +bool local_only
    }
    Component <|-- process : extends
    Class <|-- service : extends
    Component <|-- datastore : extends
    Component <|-- external : extends
    Artifact <|-- artifact : extends
    Node <|-- device : extends
    Actor <|-- system : extends
```

## Constraints

| Stereotype | Constraint |
|---|---|
| `<<service>>` | `deterministic = true` for every engine (ADR-0005); `algo_version` follows semver |
| `<<external>>` | `bind` must be `127.0.0.1` unless `optional = true` and HTTPS |
| `<<artifact>>` | Released artefacts carry a SHA-256 in `SHA256SUMS` or the model manifest |
| `<<system>>` actor | Local software only; no remote service acts on user data |
