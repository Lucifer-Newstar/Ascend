# ADR-0018: Adaptive TDEE with a Kalman Filter (tdee-v1)

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

The Fuel target came from Mifflin-St Jeor BMR x an activity factor (ADR-0005; docs/ai/ai-risks.md R16). That formula is a population average. For a given person it can be off by a few hundred kcal, and it never learns from what the scale does. docs/planning/features.md N3 asks for an adaptive calorie target from the weight trend: adherence-neutral, at most ±150 kcal per weekly change, and at least 4 weigh-ins a week.

Constraints:

- **Deterministic and pure Python.** The sidecar ships without numpy (ADR-0005, ADR-0017). The same inputs must give the same output, and the result must be explainable number by number.
- **Messy data.** Real logs have missing weigh-ins, unlogged days, partly logged days and water-weight swings of about ±1 kg.
- **The local model only explains.** It must never set a number (ADR-0005, ADR-0016).

## Decision

1. **A two-state Kalman filter** (`app/modules/intelligence/tdee.py`, `ALGO_VERSION = "tdee-v1"`). The state is [trend weight W, expenditure T].
   - **Predict, overnight from a logged day:** W += (intake - T) / 7700, and T carries over with a slow random walk.
   - **Predict, from a day with no usable intake:** weight is carried as if in balance, with a wide variance. A day under 800 kcal reads as partly logged and counts as unlogged. Missing days never stop the filter; they widen the uncertainty.
   - **Update on a weigh-in.** Several weigh-ins on one day are averaged, and each is read as a morning weigh-in. The weigh-in corrects W and, through the covariance, T.
   - **Cold start.** The prior is Mifflin-St Jeor x activity with SD 450 kcal, so the app shows a range from day 1. Status `cold_start` lasts until there are 3 weigh-ins over 7 days, then `learning`. It becomes `adaptive` once the SD is at most 200 kcal and 14 days have passed since the first weigh-in.
2. **Weekly target, adherence-neutral.** The target moves at most once a week, on Monday, from Sunday night's estimate + the goal's adjustment. It moves only when all of these hold:
   - last week had 6 of 7 days with intake and 4 or more weigh-ins;
   - the estimate is settled;
   - the change is at most 150 kcal (N3).
   Otherwise last week's target stands, and the reason is stored with the week ("intake logged on 5 of 7 days (needs 6)"). Missing a day's logging never moves the target.
3. **Values** [U]. These are tunable choices, not measured constants:
   - scale noise SD 0.8 kg;
   - intake logging SD 350 kcal (600 on an unlogged day);
   - expenditure drift 100 kcal² a day;
   - 7700 kcal per kg.
   The noise values were picked by `eval/diet_tune.py` on a tuning seed (7), inside the ranges the plan named. They were not picked on the evaluation seed.
4. **Service and API.** `diet_service.py` reads profile, meals and body metrics. Weigh-ins are averaged per day, and the history is capped at 400 days. Endpoints:
   - `GET /intelligence/tdee`: estimate ± SD, range, trend, weekly targets with reasons, completeness, and a Why with the formula and inputs.
   - `GET /intelligence/tdee/explanation`: the guarded sentence.
   The day's calorie target (the meals day log and the Today ring) becomes the adaptive one once a week has been set from the estimate. `DayLog.kcal_target_source` says which target is in use. Before then the target is the profile's Mifflin-St Jeor value, unchanged.
5. **The local model only phrases the explanation**, behind the existing coach guard (ADR-0016). An invented number, a timeout or AI off all fall back to the template.

## Consequences

### Positive

- **Learns the person.** On synthetic users the median error is 82.8 kcal at day 56, against the formula's 194.7. A 14-day weight prediction from day 56 is 50.3 % more accurate than the formula's (docs/ai/evaluation.md §5).
- **Honest about uncertainty.** The app shows a range, a status and the reason the target held or moved.
- **Fast.** The whole computation is about 3 ms for a year of data (p95 4.06 ms on the build machine). It is recomputed per request; there is no cache to go stale.

### Negative / Trade-offs

- **Slow to learn.** 57% of synthetic users are within 150 kcal on day 28, and the first two weeks are no better than the formula. Water weight hides the energy signal at first. Mitigation: the target stays on the formula until the estimate settles.
- **Under-reporting is absorbed into T.** The "you burn" figure is the expenditure that matches *logged* intake. For targets in logged calories that is what is needed, but the figure itself is biased. This is stated in the Why panel's formula.
- **Simplified physics.** 7700 kcal/kg and a constant-variance model ignore glycogen and water shifts at the start of a diet, and menstrual-cycle water.
- **The band runs slightly narrow.** ±1 SD holds the truth 61% of the time on synthetic users (nominal 68 %).
- **Synthetic evidence only.** See ADR-0017 for the limits of the simulator approach.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Keep Mifflin-St Jeor only | Never learns; off by the person's own factor forever |
| Exponential moving average of weight + energy balance over a fixed window (MacroFactor-style "trend + intake") | Similar results with less code, but no principled uncertainty, and missing days need special cases. The filter handles both |
| Bayesian regression over a rolling window | Needs matrix algebra and tuning of the window. The 2-state filter is O(days) with closed-form 2x2 updates |
| Let the local model estimate TDEE | Breaks ADR-0005: numbers come from deterministic engines, and the model only explains |
