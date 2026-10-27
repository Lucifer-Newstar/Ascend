# AI in ASCEND

> **The AI section of the docs: what the AI does, what it is never allowed to do, which model
> powers each feature and where its code lives.** Start here, then follow the index.
> Owners: **Navin** (MLOps, food classifier, evaluation) and **Jegatheesan** (sidecar AI:
> coach, model manager, scan pipeline). Status: v0.1 skeleton (2026-10-20), updated for the v6 engines (2026-10-21) and for the
> unreleased ML work on `main` and `feat/kb-gap-fill` (2026-10-27). Each feature below is marked
> **implemented** (exists in the code today, with the version it arrived in) or **planned**
> (agreed design, with its phase). The three models in `ml/` have their own cards:
> [intent router](../../ml/intent/MODEL_CARD.md), [knowledge base](../../ml/knowledge/KB_CARD.md),
> [food photo](../../ml/food/MODEL_CARD.md).

---

## 1. The principle

**Deterministic engines compute every number. AI only explains and suggests.**

- Loads, sets, readiness, XP, quests, PRs, calorie targets, nutrients, ETAs and every plan
  change come from pure, versioned Python engines
  ([ADR-0005](../architecture/adr/0005-deterministic-engines-llm-explains.md)).
- The language model receives those numbers as numbered facts and writes sentences around
  them. Its replies are checked; any reply containing a number the engines did not produce is
  replaced by the rules answer
  ([ADR-0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md)).
- The model can **suggest** a plan change only by asking the planner, which computes the
  change and shows it as a proposal the user must apply
  ([adaptive-planning-ai.md](adaptive-planning-ai.md)).
- The food classifier **suggests** dish names (top-3); the user confirms; nutrients come only
  from the INDB / IFCT / Open Food Facts database
  ([food-recognition.md](food-recognition.md)).
- Safety-critical messages (red-flag pain, eating-disorder risk, diagnosis or medicine
  questions) never reach a model; they get fixed replies.

---

## 2. AI off: the app fully works

One switch (Settings → AI, also offered at onboarding) stops every model call. Nothing
breaks, because the models were never the source of the numbers.

| Feature | AI on | AI off |
|---|---|---|
| Coach tip of the day | Rule tip, phrased by `qwen3:4b` | Rule tip as written (**implemented**) |
| Coach Q&A / chat | Model answer from facts, checked | Rules route the message (intent router when they are unsure); a cited knowledge-base passage or a help note answers (**implemented**, unreleased) |
| Weekly review | Rule findings + proposals + model summary | Same findings + proposals + template summary |
| Plan generation | Planner rules + model explanation | Planner rules + template explanation |
| Injury protocol | Rules + kind model wording | Rules + fixed wording |
| Meal photo | Classifier top-3 to confirm (the classifier runs on the CPU and is not an Ollama model) | Same; with no gated food model installed, Scan meal is hidden and food is logged by search (**implemented**, unreleased; no model trained yet) |
| Muscle map, XP, quests, PRs, TDEE | Engines | Engines (identical) |
| Next-set targets, readiness and their "Why?" | Engines; one sentence phrased by `qwen3:4b`, shown only if every number passes the coach guard | Engines; the template sentence (**implemented**, v6) |
| System notices (deload, target raised, muscle recovered) | Engines and fixed templates | Identical (**implemented**, v6) |
| Tamil | Model reply in Tamil (beta) | English templates + human-translated fixed replies |

Measured by metric R6 (the E2E journey with Ollama stopped) in
[evaluation.md](../operations/evaluation.md#product-and-reliability).

---

## 3. AI feature map

| Feature | Model | Runtime / where | Code module | Status | Doc |
|---|---|---|---|---|---|
| Tip of the day, "ask the coach" | `qwen3:4b` (prompt `P-00`) over rules `coach-rules-v1` | Ollama, GPU | `modules/coach` (`rules.py`, `ollama.py`, `runtime.py`, `service.py`) | **implemented** | [coach-llm.md](coach-llm.md) |
| Trainer chat routing | none: rules `trainer-intents-v1` first, help notes `trainer-kb-v1` | Sidecar, CPU | `modules/trainer` (`intents.py`, `kb.py`, `chat.py`) | **implemented** (1.1) | [trainer-actions.md](trainer-actions.md) |
| Intent router for messages the rules are unsure of | `ascend-intent` 1.1.0: TF-IDF n-grams + logistic regression | Sidecar, CPU, standard-library runtime (`ASCEND_INTENT_MODEL=off` disables it) | `modules/ml/intent.py`, `intent_runtime.py`, `trainer/ml_route.py`; training in `ml/intent/` | **implemented** (unreleased) | [ml/intent/MODEL_CARD.md](../../ml/intent/MODEL_CARD.md) |
| Cited knowledge answers | none: BM25 over 1,779 passages (`kb-v1.4`) | Sidecar, CPU | `modules/ml/knowledge.py`; corpus in `ml/knowledge/` | **implemented** (unreleased) | [ml/knowledge/KB_CARD.md](../../ml/knowledge/KB_CARD.md) |
| Coaching team (who answers) | none: rules over the routed topic | Sidecar | `modules/trainer/team.py` | **implemented** (unreleased) | [coaching-team.md](coaching-team.md) |
| Trainer edits and plan building from chat | none: rules (`actions-parse-v2`, plan facts) | Sidecar | `modules/actions`, `modules/planbuilder` | **implemented** (1.3; plan builder unreleased) | [trainer-actions.md](trainer-actions.md), [plan-builder.md](plan-builder.md) |
| AI setup: tiers from RAM / VRAM | none (`ai-tiers-v1`) | Sidecar | `modules/ai` (`setup.py`, `hardware.py`) | **implemented** (1.1) | [model-manager.md](model-manager.md) |
| Coach chat with streaming and tool calls | `qwen3:4b` (`P-01`, `P-02`); tiers `gemma3:4b`, `qwen3:1.7b` | Ollama, GPU | `modules/coach` + `ai/ollama_client.py` | planned · Phase 2 | [coach-llm.md](coach-llm.md) |
| Output validators and safety filter | none (rules) | Sidecar, CPU | `coach/validate.py` (number fidelity, banned phrases); no separate `coach/safety.py` | validators **implemented**; a separate safety module planned | [coach-llm.md §5–7](coach-llm.md#5-structured-output-and-validation) |
| Tip-card rephrase and "why?" | `qwen3:4b` (`P-03`, `P-04`) | Ollama | `modules/coach` | planned · Phase 2 | [prompt-library.md](prompt-library.md) |
| Weekly review summary | `qwen3:4b` (`P-05`) over rule findings | Ollama, background job | `coach/weekly_review.py` | rule findings + template summary **implemented**; model summary planned · Phase 2 | [adaptive-planning-ai.md §5](adaptive-planning-ai.md#5-the-weekly-review-every-7th-day) |
| Plan explanation, proposal reasons | `qwen3:4b` (`P-06`, `P-07`) | Ollama | `coach/planner`, `coach/proposals` | planned · Phase 2 | [adaptive-planning-ai.md](adaptive-planning-ai.md) |
| Injury follow-up wording | `qwen3:4b` (`P-08`) after rules triage | Ollama | `coach/injury` | planned · Phase 2 | [adaptive-planning-ai.md §6](adaptive-planning-ai.md#6-injury-adaptation) |
| Readiness note | `qwen3:4b` (`P-09`) | Ollama | `progress/readiness` | planned · Phase 4 | [adaptive-planning-ai.md §7](adaptive-planning-ai.md#7-readiness-check-in) |
| Tamil / Tanglish replies (beta) | `qwen3:4b` + `P-10`; fallback IndicTrans2 distilled | Ollama; CPU for IndicTrans2 | `modules/coach`, `ai/translate.py` | planned · Phase 2 (path A), Phase 4 (path B) | [multilingual-tamil.md](multilingual-tamil.md) |
| Meal photo: dish suggestions | Own classifier: food-photo v0, MobileNetV3-Small, ONNX (FP32; INT8 not started) | ONNX Runtime, **CPU** | `modules/ml/food_photo.py`, `POST /ml/food-photo`; training in `ml/` | runtime, gate and hidden Scan meal **implemented** (unreleased); **no model trained yet** | [food-recognition.md](food-recognition.md) |
| Meal photo: find items / second opinion | `qwen3-vl:2b` (`P-11`), optional | Ollama, GPU after unloading the coach | `modules/nutrition` (scan job) | planned · Phase 2 | [food-recognition.md §7](food-recognition.md#7-vlm-second-opinion-qwen3-vl2b-optional) |
| Portions | none: default unit + user quantity | Sidecar | `nutrition/portions` | planned · Phase 1 | [food-recognition.md §5.2](food-recognition.md#52-portions) |
| Nutrient values | none: database rows | SQLite | `modules/nutrition` | **implemented** (seeded search table) | [food-recognition.md §6](food-recognition.md#6-nutrients-always-from-the-database) |
| Model install, load/unload, health | none (manager) | Sidecar + Ollama API | `modules/ai` (no `model_manager.py`) | partly **implemented** (availability check, AI setup tiers) | [model-manager.md](model-manager.md) |
| Retraining from corrections | Classifier (training) | Docker + WSL2 + RTX 3050, offline | `ml/` | planned · Phase 5 | [mlops-lifecycle.md](mlops-lifecycle.md) |
| Progress photos | **none** (no AI judging in v1) | — | — | decided | [features.md §4](../planning/features.md#4-cut-or-replaced) |
| Muscle map, XP, quests, PRs, TDEE | **none** (engines) | Sidecar | `progress`, `gamification`, `workouts` | **implemented** (v0.1) | [system-architecture.md](../architecture/system-architecture.md) |
| Recovery and readiness per muscle (`recovery-v2`, personal factors `recovery-k-v1`) | **none** (deterministic engine, pure Python) | Sidecar, CPU | `modules/intelligence` (`recovery.py`, `personal.py`) | **implemented** (v6) | [ADR-0014](../architecture/adr/0014-recovery-engine-v2.md), [evaluation.md](evaluation.md) |
| Next-session targets, stall detection (`prog-v1`) | **none** (deterministic engine, pure Python) | Sidecar, CPU | `modules/intelligence/progression.py` | **implemented** (v6) | [ADR-0015](../architecture/adr/0015-progression-engine-prog-v1.md), [evaluation.md](evaluation.md) |
| "Why?" sentence for a target or a muscle (`explain-v1`) | Template; optional `qwen3:4b` phrasing behind the coach guard | Sidecar; Ollama if running | `modules/intelligence/explain.py` | **implemented** (v6); real-model phrasing **unverified** | [ADR-0016](../architecture/adr/0016-explanations-and-system-voice.md) |
| System notices for the engines | **none** (rules + templates) | Sidecar | `modules/intelligence/notices.py` | **implemented** (v6) | [ADR-0016](../architecture/adr/0016-explanations-and-system-voice.md) |

### Models at a glance

| Model | Role | Size (download) | Where it runs |
|---|---|---|---|
| `qwen3:4b` | Coach (default) | 2.5 GB (Ollama tag page) | GPU, one model at a time |
| `gemma3:4b` | Coach alternate (only if `qwen3:4b` fails the benchmark) | 3.3 GB (Ollama tag page) | GPU, likely partly CPU (estimate) |
| `qwen3:1.7b` | Coach Lite / OOM fallback | 1.4 GB (Ollama tag page) | GPU or CPU |
| `qwen3-vl:2b` | Optional meal second opinion | 1.9 GB (Ollama tag page) | GPU after the coach is unloaded |
| `ascend-food-cls` | Dish suggestions | ≈ 6 MB INT8 (estimate) | CPU, shipped in the installer |
| IndicTrans2 distilled (2 directions) | Tamil path B, only if chosen | ≈ 0.25 GB each (estimate, **unverified**) | CPU |

---

## 4. Index

| File | What it covers |
|---|---|
| [coach-llm.md](coach-llm.md) | The coach: context building, token budget, system prompt, main prompts, structured output, validators, medical safety, hallucination guards, streaming, timeouts, rules fallback, user controls, tiers |
| [prompt-library.md](prompt-library.md) | Every prompt, versioned, with variables and output schemas; fixed safety replies |
| [multilingual-tamil.md](multilingual-tamil.md) | Tamil and Tanglish (beta): what is known, two pipelines, test plan with sample prompts, rubric, go/no-go |
| [food-recognition.md](food-recognition.md) | Classifier, datasets and licences, class list, model, augmentation, training, top-3, portions, VLM second opinion, DB lookup, correction loop |
| [model-manager.md](model-manager.md) | VRAM and RAM budget, disk sizes, lifecycle state machine, GPU lock, health checks, manifest, first-run download UX |
| [trainer-actions.md](trainer-actions.md) | v1.3: what the trainer can change from chat (plan, settings, kit, profile), with examples, confirm and undo |
| [coaching-team.md](coaching-team.md) | The main trainer and the five specialists: what moves to a specialist, how the topic is picked, the handoff line, the setting |
| [adaptive-planning-ai.md](adaptive-planning-ai.md) | Rules vs AI in planning, proposals, what the AI may suggest, weekly review, injury adaptation, readiness |
| [data-and-privacy-for-ai.md](data-and-privacy-for-ai.md) | What each model sees, local-only enforcement, storage, consent for training photos, deletion |
| [evaluation-ai.md](evaluation-ai.md) | Metrics and test sets, coach rubric, latency targets, the offline eval harness, CI regression gates |
| [evaluation.md](evaluation.md) | Measured results for recovery-v2 and prog-v1 on seeded synthetic users, latency on a one-year history, and the limitations |
| [mlops-lifecycle.md](mlops-lifecycle.md) | Walkthrough: DVC, MLflow, ONNX + INT8, registry, manifest and checksums, shipping, rollback, retraining |
| [ai-risks.md](ai-risks.md) | AI risk register with mitigations, owners and signals |
| [ai-roadmap.md](ai-roadmap.md) | AI tasks per phase and member, commit-sized |

### Reading order by role

| You are | Read |
|---|---|
| Navin (MLOps, classifier) | This file → [mlops-lifecycle.md](mlops-lifecycle.md) → [food-recognition.md](food-recognition.md) → [evaluation-ai.md](evaluation-ai.md) → [ai-risks.md](ai-risks.md) |
| Jegatheesan (sidecar AI) | This file → [coach-llm.md](coach-llm.md) → [prompt-library.md](prompt-library.md) → [model-manager.md](model-manager.md) → [adaptive-planning-ai.md](adaptive-planning-ai.md) |
| Dhanush (UI) | This file → [coach-llm.md §10](coach-llm.md#10-user-controls-and-override) → [model-manager.md §7](model-manager.md#7-first-run-and-model-download-ux) → [food-recognition.md §2](food-recognition.md#2-pipeline) → [data-and-privacy-for-ai.md §4](data-and-privacy-for-ai.md#4-consent-for-training-photos) |
| Gokul (CI, packaging) | This file → [evaluation-ai.md §6](evaluation-ai.md#6-regression-gates-in-ci) → [mlops-lifecycle.md §8](mlops-lifecycle.md#8-step-6-ship-it-installer-vs-first-run-download) |

---

## 5. Decisions behind the AI

| ADR | Decision |
|---|---|
| [0004](../architecture/adr/0004-ollama-qwen3-local-llm.md) | Ollama with `qwen3:4b` (coach, Tamil beta) and `qwen3-vl:2b` |
| [0005](../architecture/adr/0005-deterministic-engines-llm-explains.md) | Deterministic engines decide; the LLM only explains |
| [0006](../architecture/adr/0006-own-food-classifier-indb-ifct.md) | Own Indian-food classifier; nutrients from INDB / IFCT |
| [0009](../architecture/adr/0009-offline-first-no-cloud.md) | Offline-first, no cloud |
| [0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md) | Prompts as versioned contracts; every model output validated |
| [0012](../architecture/adr/0012-classifier-first-meal-scan.md) | Classifier-first meal scan; VLM as an optional second opinion |
| [0014](../architecture/adr/0014-recovery-engine-v2.md) | Recovery engine v2 with personal recovery factors |
| [0015](../architecture/adr/0015-progression-engine-prog-v1.md) | Progression engine prog-v1 |
| [0016](../architecture/adr/0016-explanations-and-system-voice.md) | Explanations and the System's voice |
| [0017](../architecture/adr/0017-evaluation-synthetic-users.md) | Evaluation on seeded synthetic users |

---

## 6. Honesty rules for this section

- The only measured numbers are in [evaluation.md](evaluation.md) (v6 engines, synthetic users only, latency on the build machine). Nothing else here is measured yet. Goals are labelled **target**;
  sizes and speeds not taken from a published page are labelled **estimate**; claims we have
  not checked are labelled **unverified**.
- Model sizes are from Ollama's tag pages as recorded on 2026-10-20 and are re-checked before
  each release.
- When a measurement replaces a target, the file links the dated report in
  `docs/operations/reports/`.
