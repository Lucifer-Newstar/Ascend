# Academic evaluation plan

Status: proposed protocol, 22 November 2026. **Not executed.** A target is not a result. Keep existing dated results intact and save each new run with its own evidence.

## Separate four kinds of evidence

1. **Software correctness:** deterministic fixtures, properties, API/action tests and persistence checks.
2. **Synthetic algorithm experiments:** behaviour under a simulator's explicit assumptions, compared with simple baselines.
3. **Target-device operation:** observed Windows installer, offline, performance and backup/restore tests on named hardware.
4. **Task usability:** guide-approved consenting adult volunteers completing tasks. Not a clinical study or proof of improved training outcomes.

Neither a green CI run nor synthetic accuracy substitutes for the other evidence types.

## Baselines and tradeoffs

Use [the existing reproduction commands](../ai/evaluation.md#7-reproduce) and preserve seed, commit, configuration, raw JSON and model/data hashes. Copy outputs to a new run folder before comparing; do not silently replace the published baseline.

- Recovery: fixed 48-hour rule, population factors and personal factors. Report MAE, correlation and calibration, including sparse-history and low-readiness strata.
- Progression: repeat-last, fixed increments, linear progression with resets and prog-v1. Report target-hit rate, RIR error, too-easy and too-hard rates together. A high hit rate alone rewards trivial prescriptions.
- The current simulation reports **identical progression results when recovery is disabled** because the primary-muscle readiness never falls below the hold threshold. That experiment does not establish the benefit of coupling recovery to progression.
- Add a separately labelled stress experiment with clustered sessions/low readiness and paired hold-on/hold-off policies using the same seeds. Report how often the hold activates, target changes and opportunity costs. Keep the original experiment and this new one separate.
- Vary fatigue kernels, effort-report noise, missing logs and response assumptions. These sensitivity tests reduce dependence on one simulator but still cannot validate human physiology.

## Explanation and action cases

Freeze cases before evaluation and record expected outcomes independently of the UI under test.

| Case group | Checks |
|---|---|
| Cold start / missing effort / missing history | Missing data is visible; fallback assumptions and rule/version are exposed. |
| Progression change and recovery hold | Displayed rule, formula inputs and next target match the engine; readiness is labelled as an estimate. |
| Cancel / repeat confirm / supported undo | No pre-confirmation mutation, no duplicate write, expected audit records, correct undo or explicit non-undoable boundary. |
| Restart / backup / import | Recorded data persists; copied backup opens in an isolated test profile; no live user data is overwritten. |

A2 and A3 sample sizes/targets are in [academic scope](academic-scope.md). Unit cases establish program behaviour, not real-world fitness benefit.

## Optional language-layer evaluation

The [intent card](../../ml/intent/MODEL_CARD.md) reports 0.738 accuracy and 0.376 macro-F1 on 160 external questions, labelled by one person, with no real ASCEND-user messages. Do not report the accuracy alone. The [source ledger](../../ml/SOURCES.md) also records restrictions on some external texts; do not publish them without permission.

If this layer is assessed:

- Freeze a new, independently worded question set before tuning. Separate template-derived data from real questions and consented app-style prompts.
- Keep training/development/test separation; document who labels and how disagreements are resolved. Where feasible, use a second rater without showing the model's answer first.
- Report per-class counts/errors, macro-F1, out-of-scope recall, confidence threshold, coverage and accuracy on answered questions. Keep routing accuracy distinct from intent accuracy.
- For retrieval, report relevance with the rubric and failed examples, not merely whether a passage was returned.
- Medical/pain routing tests show response behaviour only. They do not make the router a medical safety system.
- Food-photo recognition is excluded: no trained model exists. Do not report synthetic smoke-test gates as food-recognition performance.

## Small task study, only after guide approval

Recruit 5-8 consenting adults who may stop at any time. Use a fictional profile and prepared logs, not diagnoses, injury details or personal health histories. Explain that this is a prototype and avoid asking people to perform suggested exercise or change diet. Follow the department's consent/ethics process.

Each person attempts the six A1 tasks. Record unassisted completion per participant-task attempt, time, errors and whether the person can explain one suggestion in their own words. Define assistance and completion before starting. Proposed threshold: 80% unassisted task completion. Report actual counts and failures, even if missed; do not claim significance or generalize from this small convenience sample.

Keep participant identities out of the public repository; use anonymous study IDs, minimal records, an agreed retention/deletion date and only approved aggregate outputs.

## Run report template

Create `docs/operations/reports/YYYY-MM-DD-topic.md` after testing. Include:

- Status: proposed / executed / failed / inconclusive; run date and tester.
- Commit SHA, installer filename/hash, engine/model versions, dataset hashes and seeds.
- OS, CPU/RAM/GPU, power mode, network and Ollama state.
- Commands, sample counts, timing definition, warm-up and raw-result location.
- Targets fixed before measurement, actual numerator/denominator and failures.
- Baselines, sensitivity results, limitations, interpretation and next action.

Do not put credentials, identifiable participant data, local absolute paths revealing personal information or unlicensed source texts in the report. CI status, installed-Windows checks and user-study results must have separate status labels.
