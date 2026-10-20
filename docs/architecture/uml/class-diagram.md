# Class Diagram — Core Domain

> **Diagram 2 (UML 2.5 — Structural).** The main domain classes in the sidecar and their
> relationships. Class names follow the code (`Workout`, `WorkoutSet`, `MealItem`…); attributes are the
> important ones only; full columns are in [data-model.md](../data-model.md). Services are shown where they own a formula.

```mermaid
classDiagram
    direction LR
    class Exercise {
        +int id
        +str name
        +Section section
        +str equipment
        +float met
    }
    class Muscle {
        +str code
        +float half_life_h
        +float weekly_low
        +float weekly_high
        +float capacity_es
    }
    class ExerciseMuscle {
        +float weight
    }
    class Workout {
        +int id
        +Section section
        +datetime started_at
        +int minutes
        +float session_rpe
        +session_load() float
    }
    class WorkoutSet {
        +int id
        +SetKind kind
        +float weight_kg
        +int reps
        +float rpe
        +bool completed
        +effort() float
    }
    class PR {
        +PRType type
        +float value
        +str algo_version
    }
    class MuscleLoadDaily {
        +date day_key
        +float eff_sets
        +float fatigue_end
        +str algo_version
    }
    class Meal {
        +datetime eaten_at
        +MealSlot slot
        +float kcal_total
    }
    class MealItem {
        +str unit
        +float qty
        +int oil_level
        +float kcal
    }
    class Food {
        +str source
        +str name
        +float kcal_100g
    }
    class Scan {
        +str status
        +dict model_versions
    }
    class Correction {
        +str predicted_label
        +float predicted_conf
        +int chosen_food_id
    }
    class Quest {
        +date day_key
        +QuestType type
    }
    class XpEvent {
        +int amount
        +float multiplier
    }
    class Proposal {
        +ProposalKind kind
        +dict diff
        +ProposalStatus status
    }
    class MuscleLoadService {
        <<service>>
        +ALGO_VERSION: str
        +effective_sets(muscle, window) float
        +readiness(muscle, at) float
        +status(muscle, window) LoadStatus
    }
    class PRService {
        <<service>>
        +epley(w, reps) float
        +brzycki(w, reps) float
        +detect(workout_set) list~PR~
    }
    class XpService {
        <<service>>
        +xp_to_next(level) int
        +award(event) XpEvent
    }

    Workout "1" *-- "many" WorkoutSet : contains
    WorkoutSet "many" --> "1" Exercise : of
    Exercise "1" *-- "many" ExerciseMuscle
    ExerciseMuscle "many" --> "1" Muscle
    WorkoutSet "1" --> "0..*" PR : may produce
    Muscle "1" --> "many" MuscleLoadDaily
    Meal "1" *-- "many" MealItem
    MealItem "many" --> "1" Food
    Meal "1" --> "0..1" Scan
    Scan "1" --> "0..*" Correction
    Quest "1" --> "0..*" XpEvent : rewards
    MuscleLoadService ..> WorkoutSet : reads
    MuscleLoadService ..> MuscleLoadDaily : writes
    PRService ..> PR : creates
    XpService ..> XpEvent : creates
```

## Formulas owned by the services

| Service | Formula (v2 plan) |
|---|---|
| `WorkoutSet.effort()` | 1.0 if RPE ≥ 7 · 0.5 if 5–6.5 · 0.25 below · warm-ups 0 · no RPE → 1.0 |
| `MuscleLoadService.effective_sets` | Σ weight(exercise, muscle) × effort |
| `MuscleLoadService.readiness` | 1 − min(1, F/C), F = Σ w × effort × 2^(−Δt/half_life) |
| `PRService.epley` / `brzycki` | w × (1 + reps/30) · w × 36 / (37 − reps) |
| `XpService.xp_to_next` | round(100 × L^1.3) |
