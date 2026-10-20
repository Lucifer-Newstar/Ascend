# AI Roadmap

> All AI work by phase, as commit-sized tasks with an owner, so each member's commit history
> shows the AI work they did. Every task here also appears in that member's
> `phase-plan.md`. Dates are the **estimates** from [timeline.md](../planning/timeline.md).
> Owner: **Navin** (MLOps, classifier, evaluation) and **Jegatheesan** (sidecar AI);
> **Dhanush** builds the AI screens; **Gokul** the CI gates and model packaging.

---

## 1. Phase summary

| Phase | Dates (est.) | AI outcome | Gate evidence |
|---|---|---|---|
| 0 · Foundations | 26 Oct – 8 Nov | AI decisions ratified; the v0 prompt moved into a registry; a fake Ollama for tests; food diary started | ADR-0004/0005/0006/0011/0012 accepted; coach tests run without a GPU |
| 1 · Core loop | 9 Nov – 13 Dec | Datasets versioned with licences; class list; baseline run; facts block and intent router | Baseline run in MLflow; facts formatter golden tests |
| 2 · Local AI | 14 Dec – 17 Jan | Validated coach (filters, schema, numbers, streaming, tool); classifier v0 in ONNX/INT8; scan pipeline; model manager; eval harness; Tamil path A rated | M1 baseline, M5, M6, M8, M10, M11, R6 ([evaluation.md §3](../operations/evaluation.md#3-gate-usage)); Tamil beta decision |
| 3 · Ship v1.0 | 18 Jan – 7 Feb | Pinned model digests; licences verified; classifier in the installer; v1.0 AI report | Release checklist; AI evaluation report |
| 4 · Breadth | 8 Feb – 21 Mar | Tamil path B prototype and the out-of-beta test; readiness note; Tamil UI | Tamil decision with data |
| 5 · MLOps loop | 22 Mar – 16 May | Corrections → retrain → shadow → model-only release; rollback | Retrained model beats production and ships |

AI hours to v1.0 (estimate): Navin ≈ 45, Jegatheesan ≈ 55, Dhanush ≈ 15, Gokul ≈ 8; these sit
inside each member's existing total in their phase plan, not on top of it.

---

## 2. Tasks by phase

### Phase 0 · Foundations (26 Oct – 8 Nov)

| Owner | Commit | Details |
|---|---|---|
| Navin | `docs(adr): mark ADR-0001…0012 accepted after kickoff` | Already in the phase plan; includes [ADR-0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md) and [ADR-0012](../architecture/adr/0012-classifier-first-meal-scan.md) |
| Navin | `docs(ml): start the two-week team food diary for the class list` | [food-recognition.md §3.2](food-recognition.md#32-class-list-strategy) |
| Jegatheesan | `refactor(coach): move the v0 system prompt into prompts/ with registry.yaml` | `P-00`, [prompt-library.md §1](prompt-library.md#1-how-prompts-are-stored) |
| Jegatheesan | `test(coach): fake Ollama server fixture (normal, slow, error streams)` | Lets CI test fallbacks without a GPU |

### Phase 1 · Core loop (9 Nov – 13 Dec)

| Owner | Commit | Details |
|---|---|---|
| Navin | `docs(ml): dataset SOURCES.md with the licence of every source` | Risk R6 |
| Navin | `feat(ml): v0 class list from the food diary and dataset coverage` | ≈ 45 classes, look-alike groups |
| Navin | `feat(ml): not_food image set (dvc add)` | ≈ 500 photos (estimate) |
| Navin | `feat(ml): labels.json mapping classes to INDB/IFCT ids + CI check` | Already in the phase plan |
| Navin | `feat(ml): baseline classifier run logged to MLflow` | Already in the phase plan |
| Jegatheesan | `feat(coach): facts block formatters with fact ids` | [coach-llm.md §2](coach-llm.md#2-context-building) |
| Jegatheesan | `feat(coach): intent router keyword lists (English, Tamil, Tanglish)` | Keyword rules, no model |
| Jegatheesan | `feat(nutrition): portions table with a source column` | [food-recognition.md §5.2](food-recognition.md#52-portions) |

### Phase 2 · Local AI (14 Dec – 17 Jan)

| Owner | Commit | Details |
|---|---|---|
| Navin | `feat(ml): temperature scaling and ECE in the evaluate stage` | Makes 0.80 / 0.65 thresholds meaningful |
| Navin | `feat(ml): INT8 static quantisation with a 200-image calibration set` | [mlops-lifecycle.md §6](mlops-lifecycle.md#6-step-4-export-to-onnx-and-quantise) |
| Navin | `test(ml): INT8 vs FP32 agreement and top-3 drop check` | ≥ 99% agreement (target) |
| Navin | `docs(ml): model card for ascend-food-cls v0` | [mlops-lifecycle.md §7](mlops-lifecycle.md#7-step-5-register-the-model) |
| Navin | `feat(evals): coach golden set (60 prompts + frozen facts fixtures)` | [evaluation-ai.md §3](evaluation-ai.md#3-coach-answer-quality) |
| Navin | `feat(evals): make eval-coach harness with report JSON` | [evaluation-ai.md §5](evaluation-ai.md#5-offline-eval-harness) |
| Navin | `bench(ai): VLM item recall and box usability on 30 team plates` | Decides whether "Find items for me" ships |
| Navin | `test(ai): Tamil 30-question rating, path A (decides the beta label)` | [multilingual-tamil.md §6](multilingual-tamil.md#6-go--no-go); pair: Dhanush |
| Jegatheesan | `feat(coach): prompt registry rendered with Jinja2 StrictUndefined` | `P-01 … P-11` |
| Jegatheesan | `feat(coach): JSON-schema output via Ollama format + jsonschema check` | Validator V1 |
| Jegatheesan | `feat(coach): eating-disorder, diagnosis and medicine filters with fixed replies` | `SAFE-02 … SAFE-04`; red flags are the existing routing task |
| Jegatheesan | `feat(coach): sentence-gated streaming with validators` | [coach-llm.md §5.3](coach-llm.md#53-sentence-gated-streaming) |
| Jegatheesan | `feat(coach): number-fidelity check with template fallback` | Already in the phase plan; V3 |
| Jegatheesan | `feat(coach): propose_plan_change tool without numeric arguments` | [adaptive-planning-ai.md §4](adaptive-planning-ai.md#4-what-the-ai-may-suggest) |
| Jegatheesan | `feat(coach): token budget trimming + prompt_eval_count logging` | [coach-llm.md §2.3](coach-llm.md#23-token-budget) |
| Jegatheesan | `feat(ai): refuse a non-loopback OLLAMA_HOST` | [data-and-privacy-for-ai.md §2](data-and-privacy-for-ai.md#2-what-each-model-sees) |
| Jegatheesan | `feat(ai): /api/ps check and partial-offload status` | [model-manager.md §5](model-manager.md#5-health-checks) |
| Jegatheesan | `feat(nutrition): classifier-first scan (whole photo + tapped items)` | Replaces the VLM-first scan task (ADR-0012) |
| Jegatheesan | `feat(nutrition): VLM second-opinion job with GPU handover` | [food-recognition.md §7](food-recognition.md#7-vlm-second-opinion-qwen3-vl2b-optional) |
| Jegatheesan | `feat(nutrition): personal swaps from corrections` | Deterministic, no retraining |
| Dhanush | `feat(ui): replace a chat reply in place when chat.done carries final_text` | Sentence-gate fallback |
| Dhanush | `feat(ui): tap-to-add items on the scan photo` | Multi-item plates without the VLM |
| Dhanush | `feat(ui): Use rules answer and Show in English actions under replies` | [coach-llm.md §10](coach-llm.md#10-user-controls-and-override) |
| Dhanush | `feat(ui): scan consent sheet and per-photo training checkbox` | [data-and-privacy-for-ai.md §4](data-and-privacy-for-ai.md#4-consent-for-training-photos) |
| Dhanush | `test(ai): second rater for the Tamil 30-question sheet` | Blind rating |
| Gokul | `ci: ai-safety job runs the 40-message safety suite on every PR` | [evaluation-ai.md §6](evaluation-ai.md#6-regression-gates-in-ci) |
| Gokul | `ci: ai-eval-report job checks prompt hashes, model digest and thresholds` | Turns the GPU-only eval into a CI gate |

### Phase 3 · Ship v1.0 (18 Jan – 7 Feb)

| Owner | Commit | Details |
|---|---|---|
| Navin | `chore(ai): pin Ollama model digests in models-manifest.json` | Risk R11 |
| Navin | `docs(ml): verify and record dataset and model licences before v1.0` | Risk R6; release checklist |
| Navin | `docs(operations): v1.0 AI evaluation report (classifier, coach, latency)` | Pairs with the existing v1.0 evaluation report |
| Jegatheesan | `feat(ai): unload loaded models on app quit (keep_alive 0)` | Frees the GPU for other apps |
| Jegatheesan | `fix(coach): tune timeouts from beta latency data` | [coach-llm.md §8](coach-llm.md#8-streaming-and-timeouts) |
| Gokul | `ci: bundle classifier + manifest in the installer and verify SHA-256` | [mlops-lifecycle.md §8](mlops-lifecycle.md#8-step-6-ship-it-installer-vs-first-run-download) |

### Phase 4 · Breadth (8 Feb – 21 Mar)

| Owner | Commit | Details |
|---|---|---|
| Navin | `test(ai): Tamil path A vs path B rating on 50 fresh questions` | Out-of-beta criteria |
| Navin | `docs(planning): decision on Tamil beta label (data-backed)` | Already in the phase plan |
| Jegatheesan | `feat(ai): IndicTrans2 path B prototype on CPU (int8)` | Size and speed **unverified** until this runs |
| Jegatheesan | `feat(coach): readiness note after the morning check-in` | `P-09` |
| Dhanush | `feat(ui): language setting with beta badge` | — |
| Dhanush | `feat(ui): Tamil UI strings (human-translated)` | — |

### Phase 5 · MLOps loop (22 Mar – 16 May)

| Owner | Commit | Details |
|---|---|---|
| Navin | `feat(ml): ingest_corrections.py (consent flag, perceptual-hash dedupe)` | [mlops-lifecycle.md §10](mlops-lifecycle.md#10-step-8-the-retraining-loop-opt-in) |
| Navin | `feat(ml): corrections-holdout split and two-set gate` | — |
| Navin | `docs(ai): update mlops-lifecycle.md with the real loop numbers` | — |
| Jegatheesan | `feat(nutrition): crops-only option in the corrections export` | Privacy default |
| Jegatheesan | `feat(ai): keep the previous classifier and roll back on a failed load` | [mlops-lifecycle.md §9](mlops-lifecycle.md#9-step-7-rollback) |
| Gokul | `ci: model-release workflow publishes sha256sums.txt and the manifest` | — |

Already in the phase plans before this roadmap and still part of the AI work: the job queue,
model manifest loader, resumable downloads, Ollama streaming client, GPU lock, fallbacks
table, red-flag routing, injury protocol, proposals, weekly review (Jegatheesan); classifier
v0 training, evaluate and ONNX export stages, parity test, eval gate, weighed-meal test and
the Phase 5 loop (Navin); chat UI, scan review chips, AI toggles, model download cards and
the model health page (Dhanush); the CUDA training image, `ml-eval.yml` and
`model-release.yml` (Gokul).

---

## 3. Changes made to existing phase-plan tasks

| Member | Was | Now | Why |
|---|---|---|---|
| Jegatheesan | `feat(nutrition): scan job (VLM items → crops)` | `feat(nutrition): classifier-first scan (whole photo + tapped items)` | [ADR-0012](../architecture/adr/0012-classifier-first-meal-scan.md) |
| Jegatheesan | `feat(nutrition): ONNX classifier re-rank via onnx_runtime` | `feat(nutrition): ONNX classifier top-3 via onnx_runtime` | Same decision: the classifier is primary, not a re-ranker |
| Navin | `test(ai): Tamil 30-question rating sheet and results` (Phase 4) | Phase 2 path-A rating + Phase 4 path A vs B on 50 fresh questions | The beta decision is needed before v1.0 ([ADR-0004](../architecture/adr/0004-ollama-qwen3-local-llm.md)) |

---

## 4. Definition of done for an AI task

- [ ] Status in the relevant `docs/ai/` file changed from planned to implemented in the same PR
- [ ] Prompt or model change: eval report committed and the `ai-eval-report` job green
- [ ] Works with AI off (the AI-off E2E journey still passes)
- [ ] No new number reaches the UI without an engine behind it
- [ ] The author can explain it at the gate (teach-back)
