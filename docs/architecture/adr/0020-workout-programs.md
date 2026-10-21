# ADR-0020: Workout Programs Read From the Log (programs-v1)

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

ASCEND already decides *how much* to lift for each exercise (prog-v1, ADR-0015) and *when* to back off (deload-v2). It did not say *what* to train today. The workouts contract had a planned `GET /plans/current` (`PlanOut`) since the MVP, and features.md T5 asks for a split by days per week with missed-session rules and 3+1 deload blocks.

Constraints:

- **Real life.** People miss sessions, train out of order, add an extra arm day, and import history from other apps.
- **No double bookkeeping.** A plan that has to be "started" and "completed" separately from the workout log goes stale the first time someone logs without pressing the button.
- **Deterministic and explainable**, like the other engines.

## Decision

1. **A small built-in catalog** in code (`app/modules/workouts/programs.py`, `ALGO_VERSION = "programs-v1"`):
   - Full body, 3 days;
   - Upper / lower, 4 days;
   - Push / pull / legs, 6 days;
   - Home full body, 3 days (dumbbells and a pull-up bar).
   Each program is an ordered rotation of days. Each day has exercise slots (sets x a rep zone at a target RPE, rest) and a suggested weekday. Every exercise is in the seeded library, and a unit test checks that.
2. **The next session is read from the log.** A finished gym workout counts as a program day when it trained at least half of that day's exercises; the largest overlap wins, and a tie goes to the day that was due. The next session is the day after the last program day trained. So:
   - a missed day shifts the plan and never skips a session;
   - training another day first moves the rotation on from that day;
   - an unrelated workout is ignored;
   - imported sessions count like logged ones.
3. **The engines decide the numbers.** Each slot shows:
   - the program's sets (halved in a deload-v2 week);
   - prog-v1's reps, load and RPE for that exercise;
   - the program's own rep zone when there is no history yet.
4. **Storage.** One table, `plan_enrollments` (migration 0016): which program, from which day, and when it ended. The program definitions stay in code, so a new version of a program reaches everyone without a data migration.
5. **API** (tag `workouts`, contract `workouts.yaml`, implementing the planned `/plans/current`):
   - `GET /plans/programs`: the catalog, with whether each program fits the onboarding equipment;
   - `GET /plans/current`: 404 until a program is chosen;
   - `PUT /plans/current`: choosing the current program again keeps its start;
   - `DELETE /plans/current`.
   `PlanOut` replaces the MVP placeholder schema and carries a Why.
6. **UI.** A Program card on Train (gym section):
   - the next day with each exercise's target and the sets already logged today;
   - a click opens the exercise in the logger;
   - the reason the day is next, and a Why;
   - a chooser to follow, change or stop a program.
   The seeded demo follows the PPL program it has been training.

## Consequences

### Positive

- **Nothing to keep in sync.** The plan advances from what was logged, however it was logged.
- **One source of truth per number.** Programs choose exercises, prog-v1 chooses loads, and deload-v2 chooses deload weeks.
- **Small and testable.** The pure engine has unit tests for missed days, out-of-order sessions, partial sessions and ties; the API has tests for choose, follow, change and leave.

### Negative / Trade-offs

- **Fixed catalog.** No custom programs or editing in v1. A custom program builder (and CSV plan import, C5) is future work.
- **Two different rep ranges.** prog-v1 uses the exercise's rep zone, not the program's, so a program's "5-8" can show a target at 10 reps for an exercise whose zone is 6-12. Only the program's set count is applied. Aligning them needs prog-v1 to take a zone per call.
- **The 50 % match is a heuristic.** A workout that half-overlaps two days counts as the larger overlap. It was not evaluated on real logs.
- **No calendar.** Weekdays are suggestions. Programs do not schedule sessions or send reminders.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Explicit "start program session" and "complete" | Goes stale the moment a session is logged or imported without the button |
| Calendar-based plan (Monday is always Upper A) | A missed Monday would silently skip Upper A for the week |
| Store programs in the database | Needs a migration per program change; nothing to edit them with in v1 |
| Let the local model generate a program | Not deterministic; ADR-0005 keeps the model to explaining |
