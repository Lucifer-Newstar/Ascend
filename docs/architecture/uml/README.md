# UML Diagrams — Index

> The **14-diagram UML 2.5 set** for ASCEND. Diagrams are text, so they are reviewed in
> PRs like code. **Mermaid** is used wherever Mermaid has a fitting diagram type (GitHub
> renders it natively). Mermaid has no UML use-case or timing diagram, so those two are
> **PlantUML** (render with the PlantUML VS Code extension or `plantuml` CLI).
>
> Maintainer: Navin Jairam M (Team Lead). Every diagram reflects
> [system-architecture.md](../system-architecture.md); if they disagree, the architecture
> doc wins and the diagram gets fixed.

---

## 1. Diagram Index (14)

| # | Diagram | Type | File | Notation |
|---|---------|------|------|---|
| 1 | Use Case | Behavioural | [use-case-diagram.md](use-case-diagram.md) | PlantUML |
| 2 | Class | Structural | [class-diagram.md](class-diagram.md) | Mermaid `classDiagram` |
| 3 | Object | Structural | [object-diagram.md](object-diagram.md) | Mermaid `flowchart` (instance boxes) |
| 4 | Package | Structural | [package-diagram.md](package-diagram.md) | Mermaid `flowchart` + subgraphs |
| 5 | Component | Structural | [component-diagram.md](component-diagram.md) | Mermaid `flowchart` |
| 6 | Composite Structure | Structural | [composite-structure-diagram.md](composite-structure-diagram.md) | Mermaid `flowchart` (parts + ports) |
| 7 | Deployment | Structural | [deployment-diagram.md](deployment-diagram.md) | Mermaid `flowchart` (nodes + artefacts) |
| 8 | Profile | Structural | [profile-diagram.md](profile-diagram.md) | Mermaid `classDiagram` (stereotypes) |
| 9 | Activity | Behavioural | [activity-diagram.md](activity-diagram.md) | Mermaid `flowchart` |
| 10 | State Machine | Behavioural | [state-machine-diagram.md](state-machine-diagram.md) | Mermaid `stateDiagram-v2` |
| 11 | Sequence | Behavioural | [sequence-diagram.md](sequence-diagram.md) | Mermaid `sequenceDiagram` |
| 12 | Communication | Behavioural | [communication-diagram.md](communication-diagram.md) | Mermaid `flowchart` (numbered messages) |
| 13 | Timing | Behavioural | [timing-diagram.md](timing-diagram.md) | PlantUML timing |
| 14 | Interaction Overview | Behavioural | [interaction-overview-diagram.md](interaction-overview-diagram.md) | Mermaid `flowchart` |

## 2. Conventions

| Rule | Detail |
|---|---|
| One diagram per file | Title in front matter or `title`; a short "how to read" note under it |
| Names match code | Class, module and event names are the ones in `services/sidecar/app/` and `apps/desktop/src/` |
| Stereotypes | Only those defined in the [profile diagram](profile-diagram.md) |
| Scenario | Behavioural diagrams share one scenario where possible: **"log a working set of Romanian deadlifts"** and **"scan a dosa plate"** |
| Validation | CI renders every Mermaid block with `@mermaid-js/mermaid-cli`; a parse error fails the docs job |
| Size | Keep each diagram readable on a laptop screen; split instead of shrinking |

## 3. Coverage

| Concern | Diagrams |
|---|---|
| Processes and boundaries | 5, 6, 7 |
| Domain model | 2, 3, 4 |
| Set → XP → map chain | 9, 11, 12 |
| Sidecar supervision | 10, 13 |
| Meal scan + AI fallback | 9, 11, 14 |
| Users and goals | 1 |
