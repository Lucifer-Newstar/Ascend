# ADR-0014: Recovery Engine v2: Per-Muscle Readiness from Dose, Decay and Personal Factors

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

Readiness on the muscle map came from load-v1 (`progress/muscle_load.py`). Every hard set
counted the same, and fatigue decayed with a fixed half-life per muscle. Three problems:

- an easy warm-up and a set to failure loaded a muscle the same way;
- a 12 s hold counted as a full set;
- a lifter who recovers faster or slower than average got the population numbers forever.

The constraints did not change: offline, deterministic, explainable, and the local model
never decides a number (ADR-0005). The sidecar has no numpy.

## Decision

1. **Engine:** `app/modules/intelligence/recovery.py`, `ALGO_VERSION = "recovery-v2"`. It is pure stdlib with no I/O.
2. **Dose per set** (effective sets, ES): `ES = w x I(RIR) x V`.
   - `w` is the exercise's muscle weight.
   - `I(RIR) = clamp(1 - 0.1 x max(0, RIR - 2), 0.3, 1)`. A hard set (RIR 0-2) counts fully, so the weekly bands still mean "hard sets".
   - RIR comes from logged RPE. Without RPE it comes from the e1RM inverse of the best earlier e1RM, and failing that a default of 2.
   - `V` is 0.85 for sets of 4 reps or fewer and 1.1 for sets over 20 reps.
   - Holds count seconds/30 of a set, clamped to 0.25-1.5.
   - Timed work keeps the load-time-v1 effort scale.
3. **Decay:** `F = sum ES x 2^(-hours / (h x k_g))`.
   - `h` is the muscle's population half-life from the taxonomy.
   - `k_g` is the personal factor of its muscle group (decision 5).
4. **Readiness:** `readiness = 1 - min(1, M x F / C)`.
   - `C` is the muscle's capacity.
   - `M` is the check-in modifier: `M = 1 + 0.2 (1 - sleep_unit) + soreness`, with soreness 0.10 for "some" and 0.25 for "a lot". Soreness applies only to muscles trained in the last 72 h, so `M` is between 1 and 1.45. A check-in counts for 18 h after it was saved.
   - Status bands are unchanged from load-v1. `ready_at` is when readiness reaches 0.70.
5. **Personal factors** (`personal.py`, `recovery-k-v1`): one `k` per muscle group.
   - **Response:** log session-mean RIR-adjusted e1RM.
   - **Trend:** removed per exercise with a piecewise-linear trend (knots every 6 weeks), using Frisch-Waugh-Lovell, so long-term strength gain is not read as recovery.
   - **Regressor:** the fatigue fraction at the session start under each candidate `k`.
   - **Grid posterior:** `k` from 0.6 to 1.6 and fatigue sensitivity alpha from 0 to 0.3, with a log-normal prior on `k` (sd 0.25).
   - **Output:** the posterior mean, clamped to 0.6-1.6, is used once at least 4 informative sessions exist (fatigue fraction above 0.05 at `k = 1`), with a 90 % credible interval. Otherwise `k = 1` (population).
   - **When:** refitted after every finished session over the last 365 days and stored in `recovery_params` (migration 0014).
6. **Stored doses.** Doses are written at log time into `muscle_load_events` as `recovery-v2`. Migration 0014 recomputes history, and its downgrade puts load-v1 back.
7. **Explainability.**
   - `GET /intelligence/recovery` returns every input of every readiness (F, C, h, k, M) and the population readiness beside the personal one.
   - The muscle drill-down shows "you vs population" with a Why.

## Consequences

### Positive

- Effort and holds are counted in proportion, and every number has its inputs on screen.
- On simulated users, readiness tracks the simulator's true readiness far better than a fixed 48-hour rule: Pearson r 0.907 (population factors) and 0.915 (personal) against 0.579 for typical users, 0.848 and 0.946 against 0.520 for frequent users (docs/ai/evaluation.md).
- Personal factors start at the population value and move only with evidence.

### Negative / Trade-offs

- The model shape (exponential decay, linear capacity) is an assumption. The synthetic evaluation partly shares it, so the r of about 0.9 is circular to a degree: it shows the machinery works under those assumptions, not that people recover this way. No real-user validation exists yet.
- For typical users (2-4 day gaps) `k` is barely identifiable. The fit mostly stays near 1, and the evaluation shows only a small gain over the prior for them (absolute error in `k` 0.221 against 0.235; frequent users 0.138 against 0.211).
- The refit runs inline on finishing a workout: p50 166.4 ms, p95 232.4 ms on a 1-year history on the build machine (`eval/latency.py`, `eval/results/latency.json`). Finishing a workout as a whole is p50 394.2 ms.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Keep load-v1 | Treats easy and hard sets alike; holds overcounted. |
| Fitness-fatigue (Banister) model | Needs a performance series per muscle that most users do not produce; more parameters to explain. |
| Fixed 48 h per muscle | Ignores dose; used as the evaluation baseline. |
| Count-based shrinkage `(n k_hat + N0)/(n + N0)` | Kept as `shrink_simple` for comparison; the grid posterior gives an interval and handles weak evidence better. |
| A naive centred-median performance baseline | Prototype was biased: the baseline absorbs chronic fatigue. Replaced by the trend residualisation. |

## Validation

- `tests/unit/test_recovery_v2.py`, `test_recovery_properties.py` (hypothesis), `test_recovery_personal.py`.
- `eval/recovery_eval.py`: correlation, MAE and calibration against simulated ground truth versus the fixed 48 h rule, plus `k` recovery error. Results are in docs/ai/evaluation.md.
