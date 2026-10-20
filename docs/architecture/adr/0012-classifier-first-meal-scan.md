# ADR-0012: Classifier-First Meal Scan; VLM as an Optional Second Opinion

- **Status:** Accepted (lead decision, 2026-10-20; revisit at the Phase 0 kickoff if the team objects)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead, ML owner); Jegatheesan K (scan pipeline)
- **Amends:** step 3 of [ADR-0006](0006-own-food-classifier-indb-ifct.md) (the pipeline order)

## Context

ADR-0006 and the v2 plan describe the scan as "VLM lists items and boxes → classifier
re-ranks each crop". That makes every scan depend on a 1.9 GB vision model on the GPU, which:

- forces a model swap (unload the coach, load the VLM) for every meal on a 4 GB GPU;
- makes photo logging unavailable on PCs without a suitable GPU or without Ollama;
- puts an unmeasured component first: `qwen3-vl:2b`'s item finding on Indian plates is
  **unverified** ([ml-pipeline.md §6](../ml-pipeline.md#6-llm--vlm-selection-no-training)).

Our own classifier is small, runs on CPU in about a tenth of a second per crop (target), and
is the part the team trains, evaluates and can explain.

## Decision

1. **Default scan = classifier first.** The whole photo is item 1; the user taps to add more
   items on a multi-item plate (a crop around each tap, adjustable). Each crop goes through the
   ONNX classifier on CPU → top-3 → thresholds (0.80 pre-select, 0.65 ask) → portion → DB.
2. **VLM = optional second opinion.** `qwen3-vl:2b` runs only when the user taps *Find items
   for me* or *Second opinion*, AI is on and the model is installed. It runs after the chat model
   is unloaded (GPU lock), returns boxes and labels from the allowed class list (prompt `P-11`),
   never confidences, portions or nutrients, and is unloaded afterwards.
3. **Merge rule:** VLM boxes become crops for the classifier; a VLM label inside the
   classifier's top-3 moves to chip 1 (pre-selected only if the classifier gave it ≥ 0.65); a
   label outside the top-3 is a fourth chip.
4. **Nutrients still come only from INDB / IFCT / OFF rows** (ADR-0006 unchanged there).

## Consequences

### Positive

- Photo logging works on any PC that can run the app, without Ollama or a GPU (AI-off still
  means search-and-pick, by the user's choice).
- No model swap and no extra seconds on the common path; the coach stays warm.
- The default path is fully measured by our own evaluation (top-3, calibration, latency).

### Negative / Trade-offs

- Multi-item plates need a tap per item unless the user asks for the VLM.
- The v2 plan's scan description and two existing phase-plan tasks change (updated in the
  same PR: features N2, system architecture §11, ml-pipeline §4, Jegatheesan's Phase 2 tasks).
- If the VLM proves strong on Indian plates, a later ADR may make *Find items for me* the
  default for multi-item photos.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| VLM first (ADR-0006 as written) | GPU swap on every scan; unusable without a GPU; first stage unmeasured |
| VLM only, no classifier | Dish names on Indian food unverified; no MLOps learning vehicle; violates the "measure what ships" rule |
| An object detector (for example a YOLO-family model) trained by us | Needs box labels we do not have; candidate for v1.x once corrections include boxes |

## Validation

VLM item recall ≥ 0.80 and box usability ≥ 0.70 on 30 team plates (targets) decide whether
*Find items for me* ships in v1.0; classifier metrics M1–M5 and scan latency in
[evaluation-ai.md §2](../../ai/evaluation-ai.md#2-food-classifier-and-portions).
