# Navin · Work log

> Dated record of lead / MLOps / release delivery. One row per merged change that is user-visible or
> crosses lanes. Newest at the bottom. Link the PR. Keep it factual: what shipped, not
> what is planned.

| Date | What I shipped | PR / evidence | Notes (handoff, follow-up) |
|---|---|---|---|
| 2026-10-20 | ML pipeline: preprocessing contract, prepare (dedupe/split/test-own), MobileNetV3 training with MLflow, ONNX export + parity + manifest, evaluate (top-1/3, F1, ECE), labels.json check, DVC stages; ML CI workflow with Gokul | PR #12 (`feat/ml-pipeline`) | Runs on synthetic smoke data only; real datasets, licences and the v0 model are still open |
