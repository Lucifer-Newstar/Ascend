# ml/: Indian food classifier pipeline

Photo recognition is a later phase; the MVP logs food by **search** in the seeded table.
This folder holds the working MLOps pipeline (Navin's area). It runs end to end today
on a **synthetic smoke set** so it can be tested anywhere; real training waits for the
licensed datasets and the team photo set (see [ml-pipeline.md](../docs/architecture/ml-pipeline.md)).

```
data/raw ──prepare──> data/processed ──train──> models/food_clf.pt
        ──export──> models/food_clf.onnx + models-manifest.json ──evaluate──> metrics.json
```

| Piece | Where | Status |
|---|---|---|
| Preprocessing contract (256 → crop 224, ImageNet norm) + shared test vector | `src/common.py`, `tests/test_preprocess.py` | done |
| prepare: sha256 + perceptual dedupe, size check, stratified split, team photos test-only | `src/prepare.py` | done |
| train: MobileNetV3-Small, fixed seeds, BN recalibration, MLflow logging | `src/train.py` | done (smoke data) |
| export: ONNX opset 17, parity gate vs PyTorch, SHA-256 manifest | `src/export_onnx.py` | done |
| evaluate: top-1, top-3, macro-F1, ECE, confusion; team-photo subset separately | `src/evaluate.py` | done |
| labels.json → food table check | `labels.json`, `src/check_labels.py` | done (6 classes) |
| DVC stages + MLflow project | `dvc.yaml`, `params.yaml`, `MLproject` | done |
| CI | `.github/workflows/ml.yml` | lint, tests, smoke `dvc repro` |
| Real datasets, licences, team photos, v0 model | DVC remote | **not started** |
| Temperature scaling, INT8 quantisation | | not started |

Datasets, weights and run outputs are **never committed**: `data/`, `models/*.pt|*.onnx`,
the generated manifest, `reports/`, `metrics.json` and `mlruns/` are git-ignored.

## Smoke run (any machine, CPU)

Measured 2026-10-20: `dvc repro -f` took 74 s on a 4-core Linux VM, not counting the
dependency install. Expect a different time on other machines.

```bash
cd ml
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python src/make_smoke_data.py      # synthetic shapes, NOT food photos
PATH="$PWD/.venv/bin:$PATH" dvc repro         # prepare -> train -> export -> evaluate
PATH="$PWD/.venv/bin:$PATH" dvc metrics show
.venv/bin/python -m pytest                    # 17 tests
```

Without DVC: `python src/prepare.py && python src/train.py && python src/export_onnx.py && python src/evaluate.py`.

The smoke classes are colour/shape patterns, so near-perfect scores there only prove the
plumbing works. They say nothing about food accuracy.

## Real data (when the datasets are cleared)

1. Put images under `data/raw/<class>/` and the team's consented photos under
   `data/raw/_test-own/<class>/` (they are only ever used for testing).
2. `dvc add data/raw && git add data/raw.dvc` and push to the external-drive remote.
3. Add every class to `labels.json`; `python src/check_labels.py --classes data/processed/classes.json`.
4. Set `train.pretrained: true` (ImageNet weights) and bump `export.version`.
5. `dvc repro`, then commit `dvc.lock` and `params.yaml` together.

## Experiment tracking

Runs log to MLflow in a SQLite store under `ml/mlruns/` (the file store is deprecated).
`mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db`, or set `MLFLOW_TRACKING_URI`
to the compose server (`make docker-mlflow`, the `ml` profile in `docker/docker-compose.yml`).
