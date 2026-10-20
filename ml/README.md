# ml/ (placeholder): Indian food classifier

Not part of the MVP. The MVP logs food by **search** in a seeded table; photo recognition
comes in a later phase (see the plan's ML phase). This folder holds the pipeline skeleton
so the MLOps work (Navin's area) has a home from day one.

## Planned pipeline

```
data/raw  --(prepare)-->  data/processed  --(train)-->  models/food_clf.pt
   --(export)-->  models/food_clf.onnx  --(evaluate)-->  metrics.json
```

| Piece | Tool | Status |
|---|---|---|
| Dataset versioning | DVC (`dvc.yaml`, `params.yaml`) | stub |
| Experiment tracking | MLflow, local file store (`mlruns/`) | stub |
| Model | Small CNN (e.g. MobileNetV3 / EfficientNet-B0) fine-tuned on Indian dishes | not started |
| Runtime | ONNX Runtime on **CPU** inside the sidecar (keeps the 4 GB GPU free for the LLM) | not started |
| Metric gate | top-3 accuracy on a held-out set; ONNX vs PyTorch parity on 200 images | not started |

Datasets and model files are **never committed to git**: `ml/data/raw`, `ml/data/processed`,
`ml/models/*.onnx` and `mlruns/` are in `.gitignore`; DVC tracks them instead.

## Getting started (later)

```bash
cd ml
uv venv --python 3.12 && uv pip install -r requirements.txt
dvc init --subdir           # once
dvc repro                   # runs prepare -> train -> export -> evaluate
mlflow ui --backend-store-uri ./mlruns
```

Candidate datasets (licences must be checked before use): Indian Food Images (Kaggle),
IndianFood101-style collections, plus the team's own labelled photos. Nutrition values
come from IFCT 2017 / INDB, not from the classifier.
