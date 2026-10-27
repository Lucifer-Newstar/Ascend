# Food photo model v0: how to build it on the training laptop

**Status: not trained.** Everything below has run end to end on synthetic data (prepare →
train → export → evaluate → gate, then the sidecar loading the exported ONNX file).
No food photos were downloaded and no food model exists yet. The app hides **Scan meal**
until a model that passed the gate is in the data folder.

```
Roboflow COCO exports ──coco_to_cls.py──┐
Open Images (no food) ──fetch_not_food.py──┤──> data/raw/<label>/            (training pool)
your own phone photos ─────────────────────┘    data/raw/_test-own/<label>/  (test only)
dvc repro gate:  prepare -> train (GPU) -> export (ONNX) -> evaluate -> gate (own photos)
publish_food.py -> release/food-<version>/ -> Hugging Face -> %APPDATA%\ASCEND\data\models\food
```

## 1. Your own test photos (the only set the gate trusts)

The gate scores the model **only** on photos the team took. Dataset photos are staged
and look the same across a dataset, so a score on them says little about a hostel plate.

* **30–50 photos per dish** you want the app to know. The gate needs at least 10 per dish
  (`params.yaml` `food_gate.min_own_per_class`); 30+ makes the number trustworthy.
* **Split by meal, not by shot.** Five photos of one plate count as one meal. Take 2–3
  photos per meal at most, across at least 10 different meals per dish: different days,
  places (home, mess, hotel), plates and lighting.
* Shoot from above or at about 45°, the way you would before eating, with the food
  filling most of the frame. A plate with two dishes goes in the folder of the main dish.
  Leave out photos where you cannot tell what the dish is.
* No faces and no ID cards in the frame. Photos stay on the team's machines and are never
  committed (`data/` is ignored by git).
* Optional: 30+ photos with **no food** (desk, bag, empty plate) in `_test-own/not_food`.

Folder layout: one folder per label in `ml/labels.json` (the folder name is the label),
for example:

```
ml/data/raw/_test-own/
  idli/            IMG_2031.jpg ...
  dosa/
  sambar/
  coconut_chutney/
  ...
  not_food/        (optional)
```

A dish with no own photos can still be trained, but the gate fails until every dish in
`labels.json` has its 10. Remove a dish from `labels.json` and `food/class_map.yaml` if you
will not photograph it.

## 1b. The classes (v1.4) and a smaller v0

`labels.json` lists **50 dishes** plus `not_food`. 45 of them get training crops from the
team's Roboflow export `Ascend.v1i.coco.zip` (its 59 class names are all in
`food/class_map.yaml`: 51 mapped, 8 skipped on purpose). The other 5 (`masala_dosa`,
`parotta`, `curd_rice`, `chicken_curry`, `banana`) have **no photos in that export**: they
need another dataset or must be dropped before training.

The gate rule is unchanged: **every** dish in `labels.json` needs at least 10 of your own
test photos, so the full list means about 500 own photos. That is a lot for a first model.
A v0 of 14 dishes the team eats most, each with at least 100 export crops (most with 600
or more), needs about 140 own photos:

| v0 dish (label) | export crops |
|---|---|
| idli | 1,135 |
| dosa | 961 |
| sambar | 926 |
| coconut_chutney | 1,062 |
| rice | 848 |
| ven_pongal | 618 |
| medu_vada | 814 |
| chicken_biryani | 634 |
| lemon_rice | 692 |
| boiled_egg | 666 |
| chapati | 172 |
| dal | 217 |
| omelette | 105 |
| poori | 200 |

To train that v0 without touching the gate: on the training PC, delete the other dishes
from `labels.json` and map their dataset names to `skip` in `food/class_map.yaml` (a local
change, not committed), shoot 10+ photos of each v0 dish, then run section 2. Add dishes
back in later versions as photos come in. Counts are boxes from `--list-classes`
(2026-10-26); a dish's crops can be fewer after the size check and the dedupe in prepare.

Kozhukattai is three labels (`pidi_kozhukattai`, `poorna_kozhukattai`,
`paal_kozhukattai`): they look different, differ in calories and each has about 660 crops.
`ragi_kali` assumes the export's "kali" is ragi kali; look at 20 of its photos before
training and map it to `skip` if they are the sweet ulundhu kali.

## 2. Copy-paste PowerShell (Windows 11, RTX 3050 4 GB)

Needs Git, Python 3.12, [uv](https://docs.astral.sh/uv/) and an NVIDIA driver. Run the
steps one block at a time; each line says what it does.

**Roboflow export, the clicks** (layout as of October 2026; a free Roboflow account is
needed). These were not clicked through for this PR because they need a login.
1. Open https://universe.roboflow.com/bharani-1ucid/south-indian-food-detection and sign in.
2. Click **Dataset** in the left menu and pick the newest version.
3. Click **Download Dataset**. For **Format** choose **COCO** (the "COCO JSON" one), select
   **Download zip to computer**, then **Continue**.
4. Unzip it into `ml\downloads\bharani` so that `ml\downloads\bharani\train\_annotations.coco.json` exists.
5. Do the same for https://universe.roboflow.com/microplastics-vypxl/indian-food-txofy,
   unzipped to `ml\downloads\txofy`. Optionally do IndianFoodNet, unzipped to `ml\downloads\indianfoodnet`.
6. Write the licence shown on each page into `ml\SOURCES.md`.

```powershell
# --- 0. once: environment with the CUDA build of PyTorch ---------------------------------
cd "D:\navin\Projects\Final Year Project\Ascned"   # your clone; adjust the path
git switch main; git pull --ff-only
cd ml
uv venv --python 3.12 .venv
.\.venv\Scripts\Activate.ps1
uv pip install --index-strategy unsafe-best-match -r requirements.txt
#   torch 2.14.1 has NO cu128 wheel; the cu126 build works on the RTX 3050 (CUDA True,
#   checked on the team laptop 2026-10-26). uv takes about 17 min to fetch it.
uv pip install --reinstall torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu126
python -c "import torch; print('CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
$env:MLFLOW_DISABLE_AGENT_HINT = "1"

# --- 1. training data -------------------------------------------------------------------
#   the team's own Roboflow export (all its classes are already in food\class_map.yaml):
Expand-Archive "$env:USERPROFILE\Downloads\Ascend.v1i.coco.zip" downloads\ascend -Force
python food\src\coco_to_cls.py --list-classes downloads\ascend                   # expect no UNMAPPED
python food\src\coco_to_cls.py downloads\ascend                                  # crops -> data\raw\<label>\
#   or the public Universe exports from the clicks above:
python food\src\coco_to_cls.py --list-classes downloads\bharani downloads\txofy   # check UNMAPPED names
#   add any real class name you want to keep to food\class_map.yaml, then:
python food\src\coco_to_cls.py downloads\bharani downloads\txofy                  # crops -> data\raw\<label>\
python food\src\fetch_not_food.py --limit 1500 --clean                            # data\raw\not_food\ (~150 MB)
#   copy your own photos into data\raw\_test-own\<label>\ (section 1)
python src\check_labels.py

# --- 2. prepare -> train on the GPU -> export -> evaluate -> gate ------------------------
dvc repro gate                         # estimate, not measured: 15-30 min on an RTX 3050 for ~15k crops
Get-Content models\food-gate.json      # "passed": true is needed to ship
Get-Content metrics.json | Select-String -Context 0,4 '"test_own"'
python src\check_labels.py --classes data\processed\classes.json
#   out of GPU memory? set train.batch_size: 32 in params.yaml and run dvc repro gate again
#   loader errors on Windows? set train.num_workers: 0

# --- 3. package and upload --------------------------------------------------------------
#   write the real numbers into food\MODEL_CARD.md first (it becomes the Hub README)
python food\src\publish_food.py        # -> release\food-0.1.0\ (refuses a failed gate)
uv pip install "huggingface_hub[cli]"
huggingface-cli login                  # paste a write token from huggingface.co/settings/tokens
huggingface-cli upload Lucifer-Newstar/ascend-food-v0 release\food-0.1.0 . --repo-type model   # repo name is a suggestion
#   (newer huggingface_hub names the same command `hf upload`)
git add dvc.lock params.yaml food\MODEL_CARD.md ..\ml\SOURCES.md
git commit -m "feat(ml): register food-photo v0 trained on <n> crops, own-photo top-1 <x>"
```

## 3. How the app gets the model

The model is **not** inside the installer. The sidecar looks in the data folder:

```
%APPDATA%\ASCEND\data\models\food\
  food_clf.onnx  models-manifest.json  (README.md, metrics.json)
```

To install it on a PC (the app can stay open; Fuel picks it up the next time it opens):

```powershell
uv tool run --from "huggingface_hub[cli]" huggingface-cli download Lucifer-Newstar/ascend-food-v0 --local-dir "$env:APPDATA\ASCEND\data\models\food"
```

Or download the three files from the model page and drop them into that folder. On
every request the sidecar checks that the manifest's gate says passed, that the ONNX file
matches its SHA-256, and that ONNX Runtime loads. Then **Scan meal** appears under the
food search on Fuel. It shows up to three suggestions. Picking one only adds it to the
plate; the meal is logged when you press Save. Nothing is logged from a photo by itself.
To remove the feature, delete the folder. The sidecar also reads a `food_scan_enabled`
setting (`false` hides the feature), ready for a Settings switch; no switch is in the UI yet.
`GET /ml/status` reports why it is unavailable: `missing`, `not_gated`, `checksum`,
`runtime_missing` or `disabled`.
