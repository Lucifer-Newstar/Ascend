# ADR-0015: Progression Engine prog-v1: Double Progression with RPE Autoregulation

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

The logger's "target" repeated last session's sets. Nothing told a lifter when to add
weight, when to hold, or when a lift had stopped moving. Backlog FT-1 asked for:

- a suggested next target with a one-line reason;
- a "keep mine" option that is respected;
- deload awareness.

Numbers must be deterministic and explainable (ADR-0005). Calisthenics progress through
the skill trees (`modules/skills/catalog.py`, docs/architecture/skill-trees.md).

## Decision

1. **Engine:** `app/modules/intelligence/progression.py`, `ALGO_VERSION = "prog-v1"`. It is pure, with no database or clock.
   - The service (`progression_service.py`) gathers the exercise's finished sessions (120 days), the recovery-v2 readiness of its primary muscles, the last "keep mine" decision, the skill-tree criterion it serves, and whether this is a deload week.
2. **Rep range.**
   - Use the exercise's own range when it is specific.
   - The library's generic 6-12 is replaced by a zone from the lifter's history:
     - every one of the last 6 sessions at 5 reps or fewer gives strength 3-6;
     - every one at 15 or more gives high-rep 12-20;
     - otherwise 6-10 for compounds and 8-12 for isolation.
3. **Increments.**
   - Barbell 2.5 kg (5 kg for squats, hinges and lunges); dumbbell, cable, machine and EZ-bar 2.5 kg; kettlebell 4 kg.
   - Bodyweight moves add reps, seconds or the next ladder step.
   - No step adds more than 10 % of the load. When the smallest plate is bigger than that, reps go to the top of the range + 2 first.
4. **Rules** (first match wins; target effort RPE 8 = 2 reps in reserve):
   - **kept:** "keep mine" in the last 7 days. Repeat the last session.
   - **stall_reset:** stalled. Load x 0.90.
   - **below_twice:** under the range two sessions running. Load x 0.925.
   - **below_range:** under the range once. Same load, aim for the bottom of the range.
   - **too_hard:** average RPE 9.5 or higher. Repeat.
   - **top_of_range:** every set at the top. Add one increment and go back to the bottom of the range (double progression).
   - **too_easy:** every set at RPE 7.5 or easier. Load from the RIR-adjusted e1RM for the same reps at RPE 8, at least one step and at most +10 %.
   - **add_rep:** otherwise, one more rep on the weakest set.
   - Holds follow the same shape in seconds: +10 % (at least 2 s) toward the top or the skill criterion.
   - **hold_recovering:** any increase is held when the primary muscles are under 40 % recovered.
   - **deload_week:** half the sets at RPE 7.
5. **Stall.**
   - In the current cycle (since the last load drop of 7 % or more), with at least 4 sessions, a stall is 3 sessions in a row (within 6 weeks) with no rep-at-load record.
   - Two or more stalled lifts trained in the last 14 days add the `STALLED_LIFTS` signal to the deload check (deload-v2, still "2 signals needed").
6. **Calisthenics.** When an exercise is in an open skill-tree criterion (e.g. 3x10 scapular pull-ups for the negative pull-up step), the criterion sets the target. The card says which step it feeds; meeting it once asks for the confirming session.
7. **API and UI.**
   - `GET /intelligence/progression/{id}` returns the target, the reason code, a one-line why, the formula and every input.
   - `POST .../decision` records "use it" or "keep mine" in `progression_decisions` (migration 0015).
   - `GET /intelligence/stalls` lists stalled lifts.
   - The logger shows a suggestion card (Use it / Keep mine / Why?) and fills the inputs from it.

## Consequences

### Positive

- On simulated lifters (60 users, 182 days, seed 2026), prescribed sets were hit within 1 rep on 93.1 % of exposures, against 71.8 % for linear +2.5 kg with resets and 1.7 % for a fixed +2.5 kg every session; too hard on 2.7 % against 22.4 % and 98.1 % (docs/ai/evaluation.md).
- Every suggestion carries its reason and inputs; nothing is a black box.
- The two engines agree: a target is never raised while the exercise's primary muscles are under 40 % recovered.

### Negative / Trade-offs

- **The engine errs on the easy side**, most of all without logged RPE: mean 2.43 reps more in reserve than the target overall and 3.21 for users who never log RPE; too easy (more than 4 in reserve) on 42.9 % of exposures. It cannot see reserve without RPE, so it climbs one rep at a time.
- **Stall precision is low: 0.113 (recall 0.62).** On synthetic stalls, 103 of 166 were detected and 811 flags were false alarms (5.46 per 100 progressing exposures). True plateaus are rare, and three sessions cannot separate a slow gain from noise. A false alarm costs one 10 % reset of that lift, and the deload check only uses stalls when two or more lifts stall at once.
- **Rules are thresholds chosen by us** from common coaching practice (Helms et al. 2016 for RPE 8; double progression as in Suchomel et al. 2021). They are not fitted to people.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Linear progression (+2.5 kg every session) | Simulated users failed most sets within weeks; kept as a baseline. |
| e1RM-median stall rule | First version; without RPE the e1RM follows the prescription. In development runs it gave about 9 false alarms per 100 exposures (development figure, not in `eval/results`). |
| Readiness hold at 60 % | Held so often in development runs that non-RPE users ended 10+ reps above the target reserve; 40 % kept. In the final evaluation a run without recovery input gave identical numbers, so the 40 % hold never fired there. |
| A learned policy (bandit / RL) | No real data to learn from yet; unexplainable today. Possible prog-v2 once acceptance data exists (`progression_decisions`). |

## Validation

- `tests/unit/test_progression.py` (hand-computed fixtures), `test_progression_properties.py` (hypothesis: finite, bounded jumps, deterministic, monotonic in reps and readiness), and `tests/api/test_intelligence_progression.py`.
- `eval/progression_eval.py`: hit rate, over/undershoot, too-hard and too-easy shares against repeat-last, fixed +2.5 kg and linear-with-resets baselines, and stall precision and recall.
