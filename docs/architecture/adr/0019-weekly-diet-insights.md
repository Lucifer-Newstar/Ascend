# ADR-0019: Rule-Based Weekly Diet Insights (insights-v1)

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

Fuel and Progress showed the numbers but not what they meant for the week. An insight engine is wanted that:

- says the two or three things worth knowing this week;
- has every number computed and traceable to a "Why?";
- never lets the local model invent a claim (ADR-0005, ADR-0016).

## Decision

1. **Six fixed rules** (`app/modules/intelligence/insights.py`, `ALGO_VERSION = "insights-v1"`). They run over the last 7 complete days (ending yesterday). A day counts as logged at 800 kcal or more.

   | Rule | Fires when | Needs |
   |---|---|---|
   | `intake_vs_target` | mean intake differs from the target by 10 % or more | 5 logged days |
   | `protein_short` | mean protein is below 85 % of target | 5 logged days |
   | `weekend_gap` | weekend days average 300 kcal or more above weekdays | 2 weekend + 4 weekday logs |
   | `trend_vs_goal` | the least-squares slope of 14 days' weigh-ins is outside the goal's band by more than 1 standard error. Bands: a cut loses 0.1 kg/week or more, and at most 1 % of body weight a week; a bulk gains 0.05 kg/week or more; maintenance stays within ±0.25 kg/week | 6 weigh-ins in 14 days |
   | `tdee_vs_formula` | the settled adaptive estimate differs from Mifflin-St Jeor by 150 kcal or more and 2 SD or more | tdee-v1 status `adaptive` |
   | `logging_gap` | fewer than 6 of 7 days are logged, so the weekly target holds (ADR-0018) | always checked |

2. **Report.** At most 3 findings, sorted by severity. Each finding carries a title, a sentence, its numbers, and a Why (the formula and every input). The report also lists **every rule** with its outcome: fired, quiet, or not enough data. The user can see what was checked, not only what fired.
3. **API.** Two endpoints:
   - `GET /intelligence/insights`;
   - `GET /intelligence/insights/{code}/explanation`: the local model may rephrase the finding's sentence. The coach guard checks every number against the facts, and the finding's own text is the fallback.
4. **The trend rule uses a slope with an error band, not two trend values.** The first version compared the trend weight 14 days apart, and fired on many on-plan cuts and bulks in the synthetic evaluation. The margin of 1 standard error was picked on a tuning seed (11) by `eval/diet_tune.py`.

## Consequences

### Positive

- **Explainable.** Every number on screen has a formula and inputs, and the user can see which rules stayed quiet.
- **Accurate on clean patterns.** On synthetic user-weeks (docs/ai/evaluation.md §5.2), the intake, protein and weekend rules have precision 0.935-1.0 and recall 1.0.
- **Cheap.** The engine takes well under a millisecond; the endpoint p50 is 28.23 ms on a one-year history.

### Negative / Trade-offs

- **The trend rule is weak.** Precision 0.397, recall 0.408 against the true weight. Over 14 days, water weight hides small rate differences. Its Why shows the slope and its error, so the user can judge.
- **Fixed thresholds.** 10 %, 85 % and 300 kcal suit most people, but not everyone; they are not personalised.
- **Synthetic evidence only.** Injected patterns are cleaner than real logs.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Let the local model read the week and write insights | Can invent numbers and is not reproducible (ADR-0005) |
| Statistical anomaly detection over all nutrients | Hard to explain in a sentence with a Why; needs more data than a week |
| Two-point trend comparison for the goal check | Evaluated first: too many false alarms (see Decision 4) |
