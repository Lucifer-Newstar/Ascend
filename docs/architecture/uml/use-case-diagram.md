# Use Case Diagram — ASCEND

> **Diagram 1 (UML 2.5 — Behavioural).** What the user can do with ASCEND and which
> secondary actors take part. Mermaid has no use-case notation, so this is PlantUML.
> Secondary actors are local software, not people or servers.

```plantuml
@startuml ascend-use-cases
left to right direction
skinparam packageStyle rectangle
actor "User" as U
actor "Ollama runtime" as OL <<system>>
actor "GitHub Releases" as GH <<system>>

rectangle "ASCEND desktop app" {
  usecase "Complete onboarding\n+ hardware check" as UC1
  usecase "Log workout\n(gym / calisthenics / cardio)" as UC2
  usecase "View muscle map\n+ drill-down" as UC3
  usecase "Complete daily quest" as UC4
  usecase "Log meal by search" as UC5
  usecase "Scan meal photo" as UC6
  usecase "Correct scan result" as UC7
  usecase "Chat with coach (ARC)" as UC8
  usecase "Report injury" as UC9
  usecase "Review weekly summary" as UC10
  usecase "Apply / edit / keep\nplan proposal" as UC11
  usecase "Track progress + ETA" as UC12
  usecase "Import Strong / Hevy CSV" as UC13
  usecase "Back up / export data" as UC14
  usecase "Switch AI off" as UC15
  usecase "Update app" as UC16
  usecase "Detect PR + award XP" as UC17
}

U --> UC1
U --> UC2
U --> UC3
U --> UC4
U --> UC5
U --> UC6
U --> UC8
U --> UC9
U --> UC10
U --> UC12
U --> UC13
U --> UC14
U --> UC15
U --> UC16

UC2 ..> UC17 : <<include>>
UC6 ..> UC7 : <<include>>
UC6 ..> UC5 : <<extend>>\n(fallback: AI off or timeout)
UC9 ..> UC11 : <<include>>
UC10 ..> UC11 : <<include>>
UC8 ..> UC9 : <<extend>>\n(pain mentioned)

UC6 --> OL
UC8 --> OL
UC10 --> OL
UC16 --> GH
@enduml
```

## Notes

| Use case | Works with AI off? | Feature id ([features.md](../../planning/features.md)) |
|---|---|---|
| Scan meal photo | No → falls back to *Log meal by search* | N2 |
| Chat with coach | Templates and rules answers only | C4 |
| Review weekly summary | Yes (template summary) | C3 |
| All others | Yes | — |
