# Activity Diagram — Scan a Meal Photo

> **Diagram 9 (UML 2.5 — Behavioural).** The meal-scan activity from photo to logged
> meal, with every fallback. Swimlanes are shown as subgraphs (User, Sidecar, Models).

```mermaid
flowchart TB
    start((start)) --> pick
    subgraph User
        pick[Pick or drop a photo]
        tap[Optional: tap extra items<br/>or ask Find items for me]
        confirm[Confirm chips / answer one question / adjust portion + oil]
        search[Search and pick foods]
    end
    subgraph Sidecar
        prep[Quality check, resize, strip EXIF, save to photos/meals]
        aion{AI on and<br/>classifier ready?}
        enqueue[Enqueue scan job<br/>priority 2, timeout 60 s]
        crops[Crop: whole photo + tapped items<br/>or VLM boxes]
        portion[Default unit + quantity<br/>from the food's portion table]
        lookup[INDB / IFCT lookup with ± range]
        conf{confidence}
        save[Save meal, meal_items, scan, corrections<br/>emit MealLogged]
        lockv[GPU lock: unload chat model]
        relv[Unload VLM, release GPU lock]
        fail[Explain why: dark / blurry / timeout<br/>nothing logged]
    end
    subgraph Models
        cls[ONNX classifier → top-3 per crop, CPU]
        vlm[qwen3-vl:2b → items + boxes JSON<br/>optional second opinion]
    end

    pick --> prep --> aion
    aion -- no --> search
    aion -- yes --> enqueue --> tap
    tap -- taps or none --> crops
    tap -- Find items for me --> lockv --> vlm
    vlm -- valid JSON --> relv --> crops
    vlm -- invalid / timeout --> relv
    crops --> cls --> conf
    prep -- too dark / blurry --> fail
    conf -- "≥ 0.80 pre-select" --> portion
    conf -- "0.65–0.80 chips" --> portion
    conf -- "< 0.65 one question" --> portion
    portion --> lookup --> confirm
    confirm --> save
    search --> save
    fail --> search
    save --> done((end))
```

Classifier first; the VLM runs only on request
([ADR-0012](../adr/0012-classifier-first-meal-scan.md)). Full design:
[docs/ai/food-recognition.md](../../ai/food-recognition.md).

| Guard | Value | Source |
|---|---|---|
| Pre-select threshold | ≥ 0.80 | v2 plan §10 (estimate, tune after v0) |
| Ask-one-question threshold | < 0.65 | v2 plan §10 (estimate) |
| Scan timeout | 60 s | Job queue config |
