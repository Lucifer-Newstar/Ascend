---
license: mit
library_name: onnxruntime
tags: [image-classification, food, indian-food, mobilenetv3, onnx]
---

# ASCEND food-photo v0 (MobileNetV3-Small, ONNX)

**Status: NOT TRAINED YET. No accuracy is claimed.** This card is the template the training
run fills in. Until a run passes the gate, the app hides Scan meal.

## What it is for

It suggests up to three foods from a meal photo in the ASCEND desktop app. The user always
confirms a suggestion, and the app never logs a meal from a photo by itself. It runs on
the CPU with ONNX Runtime, offline.

## Model

* MobileNetV3-Small, ImageNet-pretrained (torchvision, BSD-3-Clause), fine-tuned for 20
  epochs. AdamW, lr 0.001, cosine schedule, label smoothing 0.05, batch 64 with mixed
  precision on an RTX 3050 4 GB laptop GPU.
* Input: 224×224 RGB. Shorter side resized to 256, then centre crop, ImageNet mean/std, CHW.
* Output: logits for the dishes in `ml/labels.json` plus `not_food` (50 dishes listed in v1.4;
  a first model may train a smaller set, see [README.md](README.md) section 1b).
* Exported to ONNX opset 17, checked against PyTorch on up to 200 images (parity gate).

## Data

| Part | Source | Licence |
|---|---|---|
| Training crops | The team's Roboflow export `Ascend.v1i.coco.zip` (59 class names, mapped in `food/class_map.yaml`), plus Roboflow Universe: south-indian-food-detection (bharani-1ucid), indian-food-txofy, optional IndianFoodNet-30. Boxes are cropped by `food/src/coco_to_cls.py`. | As stated on each dataset page; the team export's licence is **not recorded yet** (see ml/SOURCES.md) |
| not_food | Open Images V7 validation photos with no food label | CC BY 2.0 per photo (authors in _ATTRIBUTION.csv); labels CC BY 4.0 |
| **Test (gate)** | The team's own phone photos, 30–50 per dish, split by meal | Ours; not published |

Splits are by source photo, so augmented copies and other boxes from one photo stay
together. Own photos are never used for training.

## Evaluation: fill in after training

| Metric (own photos only) | Value |
|---|---|
| Own photos (n) / dishes covered | _not trained yet_ |
| Top-1 | _not trained yet_ |
| Top-3 | _not trained yet_ |
| Macro-F1 | _not trained yet_ |
| ECE (calibration) | _not trained yet_ |

Gate (`ml/params.yaml` `food_gate`): at least 10 own photos for every dish, own-photo
top-1 ≥ 0.70 and top-3 ≥ 0.90, ImageNet-pretrained, and not a smoke build. Scores on the
dataset test split are reported in metrics.json but do not count.

## Limits (known before training)

* Only the dishes in `labels.json` (50 in v1.4, or the smaller v0 set the run trains).
  Anything else is forced into the closest of them or into `not_food`. 5 of the 50
  (`masala_dosa`, `parotta`, `curd_rice`, `chicken_curry`, `banana`) have no photos in the
  team export.
* `ragi_kali` assumes the export's "kali" is ragi kali (not checked yet). Tamil names are
  unreviewed (`ta_reviewed: false`).
* One dish per photo. A thali or a plate with several dishes gets the most visible one.
* Portions are not estimated. The user picks the portion count.
* Dataset photos are mostly well lit and from above; dim hostel or mess lighting will
  score lower.
* Not a medical or dietary tool. Calories come from the app's approximate food table.
