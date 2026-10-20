# Activity Diagram — Scan a Meal Photo

> **Diagram 9 (UML 2.5 — Behavioural).** The meal-scan activity from photo to logged
> meal, with every fallback. Swimlanes are shown as subgraphs (User, Sidecar, Models).

```mermaid
flowchart TB
    start((start)) --> pick
    subgraph User
        pick[Pick or drop a photo]
        confirm[Confirm chips / answer one question / adjust portion + oil]
        search[Search and pick foods]
    end
    subgraph Sidecar
        prep[Resize to 1024 px, strip EXIF, save to photos/meals]
        aion{AI on and<br/>models ready?}
        enqueue[Enqueue scan job<br/>priority 2, timeout 60 s]
        unload[GPU lock: unload chat model]
        crops[Crop each item box]
        portion[Estimate unit + count from box vs plate size]
        lookup[INDB / IFCT lookup with ± range]
        conf{confidence}
        save[Save meal, meal_items, scan, corrections<br/>emit MealLogged]
        reload[Reload chat model, release GPU lock]
        fail[Explain why: dark / blurry / timeout<br/>nothing logged]
    end
    subgraph Models
        vlm[qwen3-vl:2b → items + boxes JSON]
        cls[ONNX classifier → top-3 per crop, CPU]
    end

    pick --> prep --> aion
    aion -- no --> search
    aion -- yes --> enqueue --> unload --> vlm
    vlm -- valid JSON --> crops --> cls --> portion --> lookup --> conf
    vlm -- invalid / timeout --> fail
    conf -- "≥ 0.80 pre-select" --> confirm
    conf -- "0.65–0.80 chips" --> confirm
    conf -- "< 0.65 one question" --> confirm
    confirm --> save
    search --> save
    fail --> search
    save --> reload --> done((end))
```

| Guard | Value | Source |
|---|---|---|
| Pre-select threshold | ≥ 0.80 | v2 plan §10 (estimate, tune after v0) |
| Ask-one-question threshold | < 0.65 | v2 plan §10 (estimate) |
| Scan timeout | 60 s | Job queue config |
