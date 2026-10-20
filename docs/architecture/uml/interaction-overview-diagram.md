# Interaction Overview Diagram — A Training Day

> **Diagram 14 (UML 2.5 — Behavioural).** The day-level flow that ties the other
> interactions together. Each `ref` box points to the diagram that details it.

```mermaid
flowchart TB
    start((open app)) --> chk{first open today?}
    chk -- yes --> checkin["ref: morning check-in → readiness (v1.1)"]
    chk -- no --> dash
    checkin --> dash["Dashboard: rings, quest, muscle map"]
    dash --> choice{what next?}
    choice -- train --> log["ref: Log a working set<br/>(sequence-diagram.md)"]
    log --> more{more sets?}
    more -- yes --> log
    more -- no --> finish["WorkoutLogged → quest + XP"]
    choice -- eat --> scan["ref: Scan a meal photo<br/>(activity-diagram.md)"]
    choice -- talk --> chat["Coach chat"]
    chat --> pain{pain mentioned?}
    pain -- red flag --> stop["Fixed 'see a doctor or physio' reply"]
    pain -- mild --> injury["Injury protocol → proposal"]
    pain -- no --> chat
    finish --> rings{all 3 rings closed?}
    scan --> rings
    injury --> dash
    rings -- yes --> anim["Completion animation, streak +1"]
    rings -- no --> dash
    anim --> sunday{Sunday?}
    sunday -- yes --> review["ref: Weekly review<br/>(communication-diagram.md)"]
    sunday -- no --> endd((close))
    review --> endd
    stop --> endd
```
