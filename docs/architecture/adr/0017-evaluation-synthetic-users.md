# ADR-0017: Evaluating the Engines on Seeded Synthetic Users

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

The recovery and progression engines (ADR-0014, ADR-0015) need evidence beyond "the tests pass".

- **No real data.** We have no real multi-user training logs with ground truth: nobody measures true readiness, and real logs cannot be shared (ADR-0009, docs/ai/data-and-privacy-for-ai.md).
- **No library.** The sidecar ships without numpy or scientific libraries.

## Decision

1. **A seeded simulator** (`eval/synth.py`, pure stdlib). Each user has hidden truth:
   - per muscle group, a recovery factor `k_true` and a fatigue sensitivity;
   - per exercise, a strength curve, optionally with a plateau (an injected stall);
   - a sleep effect, noise, RPE habits (never / sometimes / always, with noise), and either an exponential or a delayed fatigue kernel.
   - The truth deliberately differs from the engines (intensity curve, per-user sleep, noisy RPE, delayed kernel), so the evaluation is not the engine grading itself.
2. **Recovery evaluation** (`eval/recovery_eval.py`):
   - predicted vs true readiness for every recently trained muscle at every session start;
   - metrics: Pearson and Spearman correlation, MAE, calibration curve and ECE, correlation with true daily capacity, and personal-factor error;
   - compared against a fixed 48-hour rule;
   - no look-ahead: personal factors are refitted every 28 days on earlier data only.
3. **Progression evaluation** (`eval/progression_eval.py`):
   - closed loop: the simulated user follows each policy's prescriptions;
   - metrics: hit rate (within 1 rep and exact), over/undershoot in reps in reserve, too-hard and too-easy shares, load error, and stall precision, recall and delay at event level;
   - baselines: repeat last session, fixed +2.5 kg, linear with resets.
4. **Latency** (`eval/latency.py`): the engines alone and the app's endpoints through the real FastAPI app on a 365-day history.
5. **Reproducibility.**
   - Fixed seeds; results committed as JSON in `eval/results/`.
   - Charts by `eval/charts.py`. matplotlib is in a separate `eval` dependency group; the app never imports it.
   - Results are written up in docs/ai/evaluation.md, including what did not work.
6. **Property tests** (hypothesis) state the invariants the engines must keep for any input. The metric code has its own unit tests (`tests/unit/test_eval_metrics.py`).

## Consequences

### Positive

- Every claim about the engines has a number, a seed and a command behind it.
- Design changes were made on evidence. Examples: the stall rule switched from an e1RM median to rep records, and the readiness hold moved from 60 % to 40 %.
- Weak spots are visible instead of hidden: stall precision 0.113 (recall 0.62), pessimistic calibration below about 0.4 predicted readiness, and the undershoot without RPE (+3.21 reps in reserve over the target).

### Negative / Trade-offs

- **Synthetic results are not real-world validity.** Every number comes from synthetic users. The simulator shares the engines' model family (stated at the top of evaluation.md), so the recovery correlation (r 0.848-0.946 for recovery-v2) is circular to a degree: it is measured against ground truth the simulator generated with a similar model. Real-user validation needs consented logs and is on the roadmap.
- **The simulator can be tuned to flatter the engine.** Mitigation, partial: the engine thresholds were chosen on small development runs (12 users, a different seed), the reported numbers come from a separate seeded run (seed 2026), and the deliberate mismatches between truth and engine are listed. Development and test users still come from the same simulator, so this is a weak guard.
- **Runtime:** the three runs took about 3, 2 and 1 minutes on the build machine, so they are not part of the PR gate. The gate runs the property tests and the metric unit tests.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Public datasets | Training logs exist, but none with measured readiness or known recovery speed; useful later for progression hit rate only. |
| Only unit tests | Shows the code does what we wrote, not whether what we wrote is useful. |
| numpy/scipy simulation | Faster to write, but adds heavy dependencies to the sidecar for evaluation only. |

## Validation

- docs/ai/evaluation.md lists the results.
- Rerunning the commands there must reproduce the recovery and progression JSON exactly (fixed seeds, deterministic code). Latency varies by machine.
