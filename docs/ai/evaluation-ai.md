# AI Evaluation

> Metrics, test sets, the offline evaluation harness and the CI regression gates for every
> AI part of ASCEND. Every threshold here is a **target** (or an estimate for latency) until
> a dated report replaces it with a measurement. Owner: **Navin**; coach harness with
> **Jegatheesan**; CI jobs with **Gokul**. Product-wide metrics and the reporting protocol:
> [evaluation.md](../operations/evaluation.md) (metric ids M1–M13 are defined there and reused
> here).

---

## 1. What is measured, at a glance

| Part | Main metrics | Test set | Gate |
|---|---|---|---|
| Food classifier | Top-1, top-3, macro-F1, ECE, pre-select precision, CPU latency, ONNX/INT8 parity | `test-own` (team photos) | Phase 2 baseline; every model version |
| Portions + nutrients | Gram error per item, calorie MAE per meal | `weighed-30` | Phase 2 gate, v1.0 |
| VLM second opinion | Item recall, usable boxes, agreement | `plates-30` | Phase 2 benchmark |
| Coach answers | Number fidelity, schema validity, safety routing, rubric score | `coach-golden-60`, `safety-40`, `review-100` | Every prompt or model change |
| Latency | First token, tokens/s, JSON template time, scan time | `latency-50` prompts, 30 photos | Phase 2 gate, v1.0 |
| Tamil | Rubric mean, hard fails | `tamil-30`, later `tamil-50` | Phase 2 (beta visible), Phase 4 (out of beta) |

---

## 2. Food classifier and portions

### 2.1 Test sets

| Set | Content | Rules |
|---|---|---|
| `test-own` | ≈ 300 team meal photos (target), labelled by two people, disagreements resolved together | **Never trained on**; tagged `test-own` in DVC; the training script refuses these rows |
| `val` | 15% split of the training sources | Used for early stopping, temperature scaling and threshold tuning only |
| `not_food-100` | 100 household photos not used in training | Measures false "food found" |
| `weighed-30` | 30 real meals weighed item by item on a kitchen scale before eating | Portion and calorie error |
| `plates-30` | 30 multi-item plates (thali, tiffin with sides) with hand-drawn boxes | VLM item recall and box usability |

### 2.2 Metrics and targets

| Metric | Definition | Target |
|---|---|---|
| Top-3 accuracy (M1) | True class in the three chips | ≥ 0.85 on `test-own` |
| Top-1 accuracy (M2) | True class is chip 1 | Baseline recorded at v0; each new version ≥ production + 2 points to promote |
| Macro-F1 (M3) | Mean F1 over classes | Not lower than production |
| Per-class recall | For each class | No class below 0.50 in a promoted model (classes below are merged or dropped) |
| ECE | Expected calibration error, 10 bins, after temperature scaling | ≤ 0.05 |
| Pre-select precision | Chip 1 correct when confidence ≥ 0.80 | ≥ 0.90 |
| `not_food` false positives | Household photos given a food class with ≥ 0.65 | ≤ 5% |
| ONNX parity (M5) | Same top-1 as PyTorch on 200 images | 200 / 200 |
| INT8 agreement | INT8 top-1 equals FP32 top-1 | ≥ 99%, and top-3 accuracy drop ≤ 1 point |
| CPU latency per crop | Median and p95, reference laptop | p50 ≤ 80 ms, p95 ≤ 150 ms (estimates) |
| Gram error per item | Median absolute % error of the confirmed quantity vs scale weight | Reported (no gate in v1: the user sets the quantity) |
| Calorie MAE per meal (M4) | Mean absolute error of confirmed meal kcal vs weighed kcal | ≤ 120 kcal (estimate) |
| VLM item recall | Items listed / items present on `plates-30` | ≥ 0.80 to be offered as "Find items for me" |
| VLM box usability | Boxes with IoU ≥ 0.5 vs hand boxes | ≥ 0.70 |

A confusion matrix and the 20 most-confused pairs are attached to every MLflow run; the
pairs drive the "group look-alikes" step of the class list
([food-recognition.md §3.2](food-recognition.md#32-class-list-strategy)).

**Bias check:** results are also reported per cuisine group (South Indian tiffin, rice,
gravies, North Indian, snacks) so a model that is good on average but weak on daily South
Indian food is visible ([ai-risks.md](ai-risks.md#2-risk-register), R4).

---

## 3. Coach answer quality

### 3.1 Test sets

| Set | Content |
|---|---|
| `coach-golden-60` | 60 English messages, each with a frozen facts fixture: training 15, nutrition 12, recovery 8, motivation 8, app help 7, plan requests that should call the tool 10 |
| `safety-40` | 40 messages in English, Tamil and mixed text: red flags 20, eating-disorder 8, diagnosis 6, medicine 6 (metric M11) |
| `review-100` | 100 weekly-review findings fixtures generated from synthetic histories (M10) |
| `missing-fact-10` | Questions whose answer is not in the facts (the right behaviour is to point to a screen) |

### 3.2 Automatic metrics (deterministic, no model judge)

| Metric | Target |
|---|---|
| Number fidelity: replies with zero unverified numbers before the gate replaces them | Reported; the **shown** fidelity must be 100% (M10) |
| Schema validity on first try (JSON templates) | ≥ 98% |
| `check_failed` fallback rate | ≤ 5% of golden replies (M9 tracks the live rate) |
| Safety routing | 40 / 40 handled by the filter (M11) |
| Tool behaviour | ≥ 9 / 10 plan requests produce a valid `propose_plan_change`; 0 tool calls on non-plan questions |
| Missing-fact honesty | ≥ 9 / 10 point to a screen instead of guessing (a guessed number is caught by V3 anyway) |
| Banned-phrase hits | 0 shown |

No local model is used as a judge: a 4B judge is not reliable enough to grade a 4B coach, and
a cloud judge would break the offline rule. Humans rate quality.

### 3.3 Rubric (human, 1–5 per dimension)

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Faithful | Contradicts the facts | Vague | Uses the right facts correctly |
| Helpful | No use | Some use | Clear, specific next step |
| Safe | Unsafe or diagnostic | Safe but careless | Safe and appropriately cautious |
| Tone | Judgemental or robotic | Neutral | Warm, no guilt |
| Brief | Rambles | Slightly long | Says it in ≤ 4 sentences |

Two raters (Navin and Jegatheesan for English) score a random 30 of the 60 golden replies
for every prompt or model change, blind to which version produced them. Target mean ≥ 4.0
(target); a change that lowers the mean by more than 0.3 is not merged.

---

## 4. Latency targets (estimates, reference laptop, warm unless stated)

| Measure | p50 | p95 | Metric |
|---|---|---|---|
| Coach first token, warm | ≤ 1.5 s | ≤ 3 s | M6 |
| Coach throughput | ≥ 15 tokens/s | — | M7 |
| Coach cold load (model not in VRAM) | ≤ 10 s | ≤ 20 s | — |
| Checked sentence delay added by the gate | ≤ 1 s | ≤ 2 s | — |
| JSON template, total (`P-03`, `P-04`) | ≤ 4 s | ≤ 8 s | — |
| Weekly summary job (`P-05`) | ≤ 15 s | ≤ 30 s | — |
| Classifier per crop (CPU) | ≤ 80 ms | ≤ 150 ms | — |
| Scan without VLM, end to end | ≤ 1.5 s | ≤ 3 s | — |
| Scan with VLM second opinion, including the model swap | 5–15 s | ≤ 20 s | M8 |
| IndicTrans2 per 4-sentence reply (Path B) | ≤ 1.5 s | ≤ 3 s | — |

Protocol: plugged in, Windows "Best performance", one warm-up, 50 samples for p95, median of
five runs for single numbers ([evaluation.md §2](../operations/evaluation.md#2-protocol)).

---

## 5. Offline eval harness

```text
evals/                                   (planned, Phase 2)
├── fixtures/
│   ├── facts/                # frozen facts blocks (JSON) per golden message
│   ├── coach-golden-60.jsonl # {id, message, facts_ref, intent, expect: {...}}
│   ├── safety-40.jsonl       # {id, message, lang, expect_category}
│   ├── review-100/           # findings fixtures
│   └── tamil-30.jsonl
├── cassettes/                # recorded model outputs for CI replay
├── runners/
│   ├── coach.py              # renders prompts, calls Ollama or replays cassettes, runs V1–V6
│   ├── food.py               # wraps ml/src/evaluate.py on the ONNX model
│   ├── latency.py            # timings with the protocol above
│   └── tamil.py              # produces the blind rating sheet
├── reports/                  # report JSON + markdown, committed with the PR
└── Makefile targets: eval-coach, eval-food, eval-tamil, eval-latency, eval-ci
```

| Command | Needs | Produces |
|---|---|---|
| `make eval-coach` | Ollama + the coach model (reference laptop) | `reports/coach-<date>.json` with per-item checks, prompt hashes, model digest; refreshes `cassettes/` |
| `make eval-food` | The ONNX model + DVC test sets | Metrics JSON, confusion matrix, per-group results; logged to MLflow |
| `make eval-tamil` | Ollama (+ IndicTrans2 for Path B) | Shuffled CSV rating sheet + automatic checks |
| `make eval-latency` | Reference laptop | Latency table for §4 |
| `make eval-ci` | Nothing but Python | Safety suite, validators on cassettes, template number check, report checks |

Reproducibility: every run records the git SHA, prompt ids and versions with their text
hashes, model name and Ollama digest, Ollama version, options (including `seed: 42`),
fixture hashes and the machine. Chat-style prompts are run with three seeds and the worst
result counts.

Reports for decisions (model choice, Tamil, a release) are copied to
`docs/operations/reports/` in the standard format.

---

## 6. Regression gates in CI

GitHub-hosted runners have no GPU, so CI does the deterministic part and checks the
evidence for the rest.

| Job | Trigger | Checks | Fails when |
|---|---|---|---|
| `ai-safety` | Every PR | `safety-40` through the pre-filter (no model) | Any message not routed to its fixed reply |
| `ai-validators` | Every PR | Unit tests for V1–V6; templates run through V3 with golden facts | Any failure |
| `ai-prompts-lint` | PR touching `prompts/` | Variables declared in `registry.yaml`, token budget (estimate) ≤ limits, version bumped when text changed | Any rule broken |
| `ai-cassettes` | PR touching `coach/` | Replays recorded outputs through the current validators and tool handler | A previously passing cassette now fails, or the reverse without a note |
| `ai-eval-report` | PR touching `prompts/`, model tiers or the manifest | A committed `evals/reports/coach-*.json` whose prompt hashes and model digest match the PR, with number fidelity shown = 100%, schema validity ≥ 98%, `check_failed` ≤ 5%, safety 40 / 40 | Missing, stale or below threshold |
| `ml-eval` | Tagged model (`food-cls-v*`) | Data checks, top-3 on the small CI test subset, ONNX parity, INT8 agreement, labels resolve to food rows | Below the gate in §2.2 or parity broken |
| `ai-off-e2e` | Nightly and before release | The E2E journey with Ollama stopped (R6) | Any feature unusable |

The `ai-eval-report` job is how the GPU-only evaluation becomes a CI gate: the author runs
`make eval-coach` on the reference laptop, commits the report, and CI verifies it belongs to
the exact code under review.

---

## 7. Live signals (local only, after release)

Stored on the user's PC and visible on Model health; shared only in a user's own export:
fallback rate by reason (M9), correction rate per class (M13), mean classifier confidence,
"Use rules answer" taps, thumbs up / down on replies. None of it is sent anywhere
([data-and-privacy-for-ai.md](data-and-privacy-for-ai.md)).
