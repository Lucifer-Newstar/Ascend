# Navin · Lead / MLOps / Releases Phase Plan

> **Purpose:** my delivery, handoffs and commit-sized tasks by phase. Shared scope: [features](../../planning/features.md). Gates: [phases](../../planning/phases.md). Dates (estimates): [timeline](../../planning/timeline.md). Tick a box when the commit is merged. Hours (estimate): ~135 to v1.0.

| Phase | I deliver | I need | Handoff / completion check |
|---|---|---|---|
| **0 · Foundations** | Repo rules, docs, ADRs ratified, kickoff, tracker | Team at kickoff | Gate run; decisions logged |
| **1 · Core loop** | Formula specs, evaluation protocol, DVC + MLflow, meal photos, baseline classifier | Compose from Gokul | Specs merged with worked examples; baseline run in MLflow |
| **2 · Local AI** | Classifier v0, ONNX + parity, eval gate, model manifest, benchmarks | Training image from Gokul; scan pipeline from Jegatheesan | Classifier wired in the app; gate job green |
| **3 · Ship v1.0** | Release notes, go/no-go, rollback drill, v1.0 evaluation report | Release workflow from Gokul | `v1.0.0` published; report in `operations/reports/` |
| **4 · Breadth** | Tamil rating + decision, classifier v1 (more classes), evaluation update | Raters (Dhanush) | Tamil label decided with data |
| **5 · MLOps loop** | Corrections → DVC v2, drift report, retrain + promote, shadow eval, model-only release | Corrections export from Jegatheesan | Retrained model beats production and ships as a model-only update |

## Commit-sized tasks

### Phase 0 · Foundations (26 Oct – 8 Nov)

- [ ] `docs: add docs/ folder (architecture, planning, team, members)`
- [ ] `chore(meta): CODEOWNERS, PR template, issue templates`
- [ ] `chore(meta): branch protection notes + labels in CONTRIBUTING`
- [ ] `docs(meta): README with AI-assistance line, quickstart, screenshots`
- [ ] `docs(adr): mark ADR-0001…0010 accepted after kickoff`
- [ ] `docs(planning): kickoff minutes and decision log K1–K8`
- [ ] `docs(planning): tracker updated for the Phase 0 gate`

### Phase 1 · Core loop (9 Nov – 13 Dec)

- [ ] `docs(architecture): load model spec with worked hamstring example`
- [ ] `docs(architecture): XP, quests and streak spec with examples`
- [ ] `docs(architecture): energy targets and ETA spec with examples`
- [ ] `docs(operations): evaluation protocol and report template`
- [ ] `feat(ml): ml/ skeleton with params.yaml and dvc.yaml stages`
- [ ] `feat(ml): DVC remote on external drive + first dataset import`
- [ ] `feat(ml): prepare stage (dedupe, resize, split, label map)`
- [ ] `feat(ml): labels.json mapping classes to INDB/IFCT ids + CI check`
- [ ] `feat(ml): collect and dvc add 300 team meal photos (test-own tag)`
- [ ] `feat(ml): baseline classifier run logged to MLflow`
- [ ] `test(ml): training refuses rows tagged test-own`

### Phase 2 · Local AI (14 Dec – 17 Jan)

- [ ] `bench(ai): coach model tokens/s, first token and VRAM on reference laptop`
- [ ] `docs(adr): update ADR-0004 with benchmark results`
- [ ] `feat(ml): train classifier v0 with fixed seeds (timm backbone)`
- [ ] `feat(ml): evaluate stage (top-1, top-3, macro-F1, confusion matrix)`
- [ ] `feat(ml): ONNX export stage`
- [ ] `test(ml): ONNX parity on 200 images`
- [ ] `test(ml): preprocessing test vector shared with sidecar`
- [ ] `ci(ml): eval gate in ml-eval.yml compares with production` (pair: Gokul)
- [ ] `feat(ml): register v0 in MLflow and write models-manifest.json`
- [ ] `test(ml): 30 weighed reference meals for calorie MAE` (pair: Jegatheesan)

### Phase 3 · Ship v1.0 (18 Jan – 7 Feb)

- [ ] `docs: CHANGELOG for v0.1–v1.0`
- [ ] `docs(operations): v1.0 evaluation report (R/M/E metrics)`
- [ ] `docs(operations): rollback drill report` (pair: Gokul)
- [ ] `chore(release): v1.0.0-beta.1`
- [ ] `chore(release): v1.0.0`

### Phase 4 · Breadth (8 Feb – 21 Mar)

- [ ] `test(ai): Tamil 30-question rating sheet and results`
- [ ] `docs(planning): decision on Tamil beta label (data-backed)`
- [ ] `feat(ml): extend classes with team photos (classifier v1)`
- [ ] `docs(operations): evaluation update for v1.1`

### Phase 5 · MLOps loop (22 Mar – 16 May)

- [ ] `feat(ml): ingest exported corrections into DVC dataset v2`
- [ ] `feat(ml): weekly drift report (confidence, correction rate, class mix)`
- [ ] `feat(ml): retrain v1 and compare runs in MLflow`
- [ ] `feat(ml): shadow evaluation script (agreement with user picks)`
- [ ] `chore(release): model-only release ascend-food-cls v1.x`
- [ ] `docs(operations): MLOps loop report`

## Lead completion check (each phase)

- [ ] Gate checklist run with the team; minutes in the decision log
- [ ] Tracker and timeline updated
- [ ] My own `ml/` commits explained at the gate (teach-back)
- [ ] Work log updated
