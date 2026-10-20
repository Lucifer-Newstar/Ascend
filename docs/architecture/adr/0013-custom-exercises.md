# ADR-0013: Custom Exercises: Rules First, Local Model Second, Online Only on Request

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead)

## Context

The bundled library (free-exercise-db plus ASCEND's own calisthenics progressions) will
never cover everything people train. Users need to add their own exercises, and those
exercises must work everywhere a library exercise works: muscle load, quests, stats,
history, import/export.

What a custom exercise needs is muscles mapped onto the 19 regions, a measure (reps, hold
or time), a section and a pattern. If those are wrong, readiness and quests go wrong too. At the same time:

- the app is offline-first (ADR-0009);
- AI is optional and only explains or suggests (ADR-0005, ADR-0011);
- users must be able to see where every value came from.

## Decision

1. **Analyse, review, then create.** `POST /exercises/analyze` proposes every field.
   Nothing is saved until the user confirms the form (`POST /exercises`).
2. **Four stages, each optional except rules.** Each field records the stage that set it in `field_sources`:
   1. `library`: fuzzy match against the library.
      - Close matches are offered as "did you mean".
      - A match scoring 0.85 or more seeds the proposal.
      - An exact or alias match blocks creation (409), which prevents duplicates.
   2. `rules`: keyword rules for equipment, section, measure, pattern, muscles, difficulty and rep range.
      The rules always produce a complete proposal.
   3. `local_ai`: qwen3:4b through Ollama on localhost, prompt `exercise_classify.v1`, with a JSON schema sent as `format`.
      - The reply is validated field by field: enum values, known muscle regions, at least one primary muscle, instruction length.
      - Invalid fields are dropped and the earlier value stays.
      - If AI is off, the model is not installed, or the reply is invalid or errors, the stage is skipped and its status is reported. The flow never blocks on the model.
   4. `wger`: an exact-name lookup on wger.de.
      - It runs **only** when Settings → "Online exercise lookup" is on (off by default, enabled behind an explicit consent dialog) **and** the user ticks "also look up online" for that exercise.
      - wger's licence and a link are stored as attribution.
3. **The user has the last word.** Any field the user edits in the review form is sent with source `user`.
   The detail page shows each field's source.
4. **Strict validation on create.**
   - Muscle regions must be known; weights must be between 0.25 and 1, with no duplicates.
   - At least one region is required, except for mobility and meditation.
   - `rep_low` must be ≤ `rep_high`.
   - MET is accepted only for time-based exercises.
   - Instruction and alias lengths are bounded.
   - A custom hold exercise follows the same rules as library holds (seconds are required).
5. **Event.** Creation publishes `ExerciseAdded` (with `field_sources`) through the outbox, so the future intelligence layer knows which fields were guessed.
6. **Removal archives.** Removing a custom exercise archives it: it is hidden from the library and pickers, but its sets, PRs and stats stay. Library exercises cannot be removed.
7. **Quests.** Quest suggestions draw from ASCEND's core list, the user's custom exercises and any library exercise they have logged. Quest progress counts sets by muscle, so custom exercises count automatically.

## Consequences

### Positive

- Works fully offline. With no model installed, the rules proposal is complete and still reviewable.
- Every value is traceable to its source, which matters for a 4B model's guesses.
- Duplicates of library exercises are caught before they split a user's history.

### Negative / Trade-offs

- Keyword rules are crude for unusual names. The review step exists for exactly this, and the model or wger can improve the proposal.
- wger's public API only filters by exact name (its search endpoint is not available), so the online lookup finds exercises only when the name matches wger's.
- Muscle weights from wger and from the model are coarse (primary 1.0, secondary 0.5).

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Model-first, rules as fallback | The model is optional and may be absent. Rules-first gives the same baseline on every machine, and the model's output can only refine it |
| Free-text muscles | They would break muscle load and quests, which key on the 19 regions |
| wger on by default | Contradicts offline-first and the privacy promise. The user must opt in, then ask per exercise |
| Hard delete | Would orphan logged sets and PRs |

## Validation

- `tests/api/test_custom_exercises.py` covers: the rules-only path, library matches and duplicates, the model mocked (valid, invalid and error replies), no model installed, online lookup gated by the setting and the per-request ask (wger mocked), creation, then logging, muscle load, the outbox event and quest refs, validation errors and archiving.
- `tests/unit/test_custom_rules.py` covers the keyword rules.
