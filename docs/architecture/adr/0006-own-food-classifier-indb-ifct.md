# ADR-0006: Own Indian-Food Classifier + INDB/IFCT Nutrient Database

- **Status:** Accepted (lead decision, 2026-10-20; revisit at the Phase 0 kickoff if the team objects)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead, ML owner); Jegatheesan K (integration)

## Context

Generic food models and Western databases handle sambar, chutneys, dosa or biryani
poorly. A small VLM can list items on a plate but its dish names and its nutrient
guesses are unreliable. The project also needs a real MLOps learning vehicle with
datasets, experiments, a registry and an evaluation gate.

## Decision

1. **Nutrients only from databases:** INDB (1,014 recipes, per 100 g and per serving),
   IFCT 2017 (raw ingredients), Open Food Facts India subset (packaged). Never from a model.
2. **Our own classifier** (owner: Navin): a small CNN (timm backbone, final choice by
   benchmark) trained on the Indian Food Images Dataset (4,000 images, 80 classes, per its
   listing) with Food-101 transfer, exported to **ONNX** and run on **CPU** in the sidecar.
3. Pipeline: VLM lists items + boxes → classifier re-ranks each crop (top-3) → portion
   units (katori, ladle, cup, piece, tbsp) + oil level → DB lookup with a ± range →
   user confirms; every edit is stored as a correction. **Amended by
   [ADR-0012](0012-classifier-first-meal-scan.md):** the classifier runs first on the whole
   photo and on user-tapped items; the VLM is an optional second opinion.
4. Team photos are the **test set only**. Pipeline details: [ml-pipeline.md](../ml-pipeline.md).

## Consequences

### Positive

- Indian dishes named correctly more often than with a VLM alone (to be measured).
- Numbers are traceable to a database row with a licence.
- A complete, explainable MLOps project: DVC, MLflow, gate, ONNX parity, drift, retraining.

### Negative / Trade-offs

- Labelling and training effort; 80 classes won't cover every regional dish (search fallback).
- Dataset licences must be checked before redistribution (marked unverified in data-model.md).
- Portion estimation from a photo stays rough (often ±20% or more, estimate) — the UI shows ranges.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| VLM names dishes and estimates calories | Unreliable numbers; untestable; violates ADR-0005. |
| Hosted food API (e.g. commercial nutrition APIs) | Needs internet and accounts; Indian coverage varies. |
| Search-only logging | Kept as the fallback, but photo logging is a core feature request. |
