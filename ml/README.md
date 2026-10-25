# ml/: ASCEND's on-device models

Navin's area. Three models, each with its own card, all tracked with DVC and MLflow:

| Model | Status | Card |
|---|---|---|
| Trainer-chat **intent router** (`intent/`) | **Trained and shipped** in the sidecar. 0.713 accuracy on 160 real questions. | [intent/MODEL_CARD.md](intent/MODEL_CARD.md), [intent/DATA_CARD.md](intent/DATA_CARD.md) |
| **Knowledge base** for cited answers (`knowledge/`) | **Built and shipped**: 1,473 passages, BM25. On real questions a relevant passage ranks first for 35%. | [knowledge/KB_CARD.md](knowledge/KB_CARD.md) |
| **Food photo** classifier v0 (`src/`, `food/`) | **Not trained.** Pipeline, gate and app integration are ready; it waits on datasets, the team's photos and a GPU run. | [food/MODEL_CARD.md](food/MODEL_CARD.md), [food/README.md](food/README.md) |

Sources and licences for all of them: [SOURCES.md](SOURCES.md).

The food pipeline below runs end to end on a **synthetic smoke set**, so it can be tested
anywhere. Real training follows [food/README.md](food/README.md) (see also
[ml-pipeline.md](../docs/architecture/ml-pipeline.md)).

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
| gate: own photos only, every dish covered, pretrained, never a smoke build | `src/gate.py` | done |
| Roboflow COCO → crops (class map), Open Images not-food fetch | `food/src/coco_to_cls.py`, `food/class_map.yaml`, `food/src/fetch_not_food.py` | done (fetch checked on 6 photos) |
| GPU training (CUDA, mixed precision) | `src/train.py`, `params.yaml` | done, not yet run on a GPU |
| release packaging for Hugging Face | `food/src/publish_food.py` | done |
| labels.json → food table check | `labels.json`, `src/check_labels.py` | done (18 dishes + not_food) |
| DVC stages + MLflow project | `dvc.yaml`, `params.yaml`, `MLproject` | done |
| CI | `.github/workflows/ml.yml` | lint, tests, smoke `dvc repro` |
| Real datasets, licences, team photos, v0 model | DVC remote, [food/README.md](food/README.md) | **not started** (Navin's GPU run) |
| Temperature scaling, INT8 quantisation | | not started |

Datasets, weights and run outputs are **never committed**: `data/`, `models/*.pt|*.onnx`,
the generated manifest, `reports/`, `metrics.json` and `mlruns/` are git-ignored.

## Smoke run (any machine, CPU)

Measured 2026-10-20: `dvc repro -f` took 74 s on a 4-core Linux VM, not counting the
dependency install. Expect a different time on other machines.

```bash
cd ml
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt --index-strategy unsafe-best-match
.venv/bin/python src/make_smoke_data.py      # synthetic shapes, NOT food photos
# the smoke run trains from scratch: set train.pretrained false and a -smoke version
# (CI does this), otherwise the run downloads ImageNet weights
PATH="$PWD/.venv/bin:$PATH" dvc repro gate    # prepare -> train -> export -> evaluate -> gate
PATH="$PWD/.venv/bin:$PATH" dvc metrics show
.venv/bin/python -m pytest                    # 43 tests
```

Without DVC: `python src/prepare.py && python src/train.py && python src/export_onnx.py && python src/evaluate.py`.

The smoke classes are colour/shape patterns, so near-perfect scores there only prove the
plumbing works. They say nothing about food accuracy.

## Real data (when the datasets are cleared)

1. Put images under `data/raw/<class>/` and the team's consented photos under
   `data/raw/_test-own/<class>/` (they are only ever used for testing).
2. `dvc add data/raw && git add data/raw.dvc` and push to the external-drive remote.
3. Add every class to `labels.json`; `python src/check_labels.py --classes data/processed/classes.json`.
4. `train.pretrained` is already true (ImageNet weights); bump `export.version` per model.
5. `dvc repro gate`, then commit `dvc.lock` and `params.yaml` together. The full Windows
   GPU run, upload and install steps are in [food/README.md](food/README.md).

## Experiment tracking

Runs log to MLflow in a SQLite store under `ml/mlruns/` (the file store is deprecated).
`mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db`, or set `MLFLOW_TRACKING_URI`
to the compose server (`make docker-mlflow`, the `ml` profile in `docker/docker-compose.yml`).

## Intent router and knowledge base

```bash
PATH="$PWD/.venv/bin:$PATH" dvc repro intent_evaluate kb_evaluate   # downloads ~60 MB of sources
python intent/src/publish.py && python knowledge/src/publish.py    # copy into the sidecar assets
```

Both run on a CPU. Their gates, metrics and limits are in their cards. Their sidecar code
is in `services/sidecar/app/modules/ml/`.
