# Sequence Diagram — Log a Working Set

> **Diagram 11 (UML 2.5 — Behavioural).** What happens between pressing Enter on a set
> and the muscle map changing colour, as implemented in the v0.1 skeleton (handlers run
> inline in the request's transaction), with the Phase 1 push step shown at the end.
> Target: < 150 ms end to end (estimate).

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant R as Renderer
    participant P as Preload
    participant M as Main
    participant A as Sidecar API
    participant W as workouts.service
    participant B as EventBus
    participant PR as progress (muscle load)
    participant G as gamification (XP, quests)
    participant DB as SQLite

    U->>R: Enter on set row (70 kg × 8 @ RPE 8)
    R->>P: window.ascend.request(POST /workouts/412/sets)
    P->>M: invoke sidecar:request
    M->>M: check state = ready, add Bearer token
    M->>A: POST /workouts/412/sets
    A->>W: log_set(workout 412, SetIn)
    W->>DB: INSERT workout_sets (same transaction)
    W->>W: e1RM (Epley) vs previous best → is_pr
    W->>B: publish SetLogged(set_id, exercise_id, rpe, is_pr)
    B->>PR: on SetLogged
    PR->>DB: INSERT muscle_load_events (hamstrings 1.0, glutes 0.5 …)
    B->>G: on SetLogged
    G->>DB: INSERT xp_events, update quest_items
    W->>DB: COMMIT (set, load and XP together)
    A-->>M: 201 LoggedSet {set, xp_awarded, previous_best_e1rm}
    M-->>R: SidecarResponse
    R-->>U: row done, rest timer, PR toast if e1RM beat previous best
    R->>M: request(GET /dashboard)
    M->>A: GET /dashboard
    A-->>R: rings, muscles, game summary
    R-->>U: map recolours, XP bar moves
    Note over A,R: Phase 1: outbox dispatcher + SSE dashboard.changed replaces the re-fetch
```

## Alternative: sidecar not ready

If the supervisor is not `ready` at step 4, `request` rejects (`sidecar is restarting`);
the renderer keeps the row as "unsaved" and retries once `ready` returns. From Phase 1 the
request carries an idempotency key (the set's uuid) so a retry can never log the set twice.
