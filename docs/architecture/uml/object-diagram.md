# Object Diagram — One Logged Set, One Moment

> **Diagram 3 (UML 2.5 — Structural).** A snapshot of real instances right after the
> user logs a working set of Romanian deadlifts (sample data, consistent with the v2
> mockups). Mermaid has no object notation, so instances are boxes named
> `instance : Class` with their slot values.

```mermaid
flowchart LR
    w412["w412 : Workout<br/>section = gym<br/>started_at = 2026-11-20 18:05<br/>session_rpe = 7.5"]
    ws9921["ws9921 : WorkoutSet<br/>kind = working<br/>weight_kg = 70<br/>reps = 8<br/>rpe = 8<br/>completed = true"]
    rdl["ex17 : Exercise<br/>name = Romanian deadlift<br/>section = gym"]
    m1["em1 : ExerciseMuscle<br/>weight = 1.0"]
    m2["em2 : ExerciseMuscle<br/>weight = 0.5"]
    ham["hamstrings : Muscle<br/>half_life_h = 36<br/>weekly 10–16"]
    glu["glutes : Muscle<br/>half_life_h = 36<br/>weekly 6–14"]
    pr["pr301 : PR<br/>type = e1rm<br/>value = 88.7 kg<br/>formula = epley"]
    load["mld_ham_1120 : MuscleLoadDaily<br/>eff_sets = 3.0<br/>algo_version = load-1.0.0"]
    xp["xp8812 : XpEvent<br/>kind = pr<br/>amount = 40"]

    w412 --- ws9921
    ws9921 --- rdl
    rdl --- m1 --- ham
    rdl --- m2 --- glu
    ws9921 --- pr
    ham --- load
    pr --- xp
```

## Checks on the values

| Value | Derivation |
|---|---|
| e1RM 88.7 kg | Epley: 70 × (1 + 8/30) = 88.67 |
| Effort 1.0 | RPE 8 ≥ 7 |
| Hamstrings +1.0 ES, glutes +0.5 ES for this set | primary 1.0, secondary 0.5 |
| eff_sets = 3.0 | three such working sets today |
| XP 40 | "New PR" row of the XP table |
