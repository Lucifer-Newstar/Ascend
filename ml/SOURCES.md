# ML data sources and licences

Every dataset, document and model that the ML work in `ml/` reads or ships. Licences were
read on each source's own page on 2026-10-25. Raw downloads are never committed: they are
DVC outputs (`intent/raw`, `knowledge/raw`, `data/raw`) and are git-ignored.

## Shipped inside the app

| What ships | Built from | Licence of the source | How it is used |
|---|---|---|---|
| `intent_model.json.gz` (intent router weights) | Fitness Stack Exchange titles, CLINC150, team templates | CC BY-SA 4.0 (Stack Exchange), CC BY 3.0 (CLINC150), MIT (templates) | Only learned weights over word and character n-grams ship. No question text ships. See [intent/DATA_CARD.md](intent/DATA_CARD.md). |
| `knowledge.jsonl.gz`: 871 passages | [free-exercise-db](https://github.com/yuhonas/free-exercise-db) | Unlicense (public domain) | Exercise steps, quoted with the source shown |
| `knowledge.jsonl.gz`: 306 passages | [Physical Activity Guidelines for Americans, 2nd ed. (2018)](https://odphp.health.gov/sites/default/files/2019-09/Physical_Activity_Guidelines_2nd_edition.pdf), HHS | US federal government work, public domain (17 U.S.C. 105) | Paragraphs, each cited with its PDF page |
| `knowledge.jsonl.gz`: 61 passages | [USDA FoodData Central, SR Legacy](https://fdc.nal.usda.gov/) | CC0 1.0; USDA asks for a citation | Per-100 g values for 61 foods (see `knowledge/usda_foods.yaml`) |
| `knowledge.jsonl.gz`: 6 passages | [WHO physical activity fact sheet](https://www.who.int/news-room/fact-sheets/detail/physical-activity) and the WHO 2020 guidelines | WHO text is CC BY-NC-SA 3.0 IGO, so **none of it is copied** | Our own summary, written in our own words (`knowledge/notes/who_2020.md`, MIT) |
| `knowledge.jsonl.gz`: 188 passages | The app's own food table (`services/sidecar/app/modules/nutrition/seed*.py`) | MIT (ASCEND) | Approximate household-portion values. No IFCT/INDB tables are copied. |
| `knowledge.jsonl.gz`: 41 passages | Team notes (`knowledge/notes/*.md`) | MIT (ASCEND) | General guidance. Where a number comes from a published position (for example ISSN on protein), the note cites it. ICMR-NIN material appears only as short summaries we wrote ourselves, with the citation. **Not reviewed by a medical professional.** |

## Used for training or evaluation only (nothing ships)

| Source | Licence | Use |
|---|---|---|
| Fitness Stack Exchange data dump, `fitness.stackexchange.com.7z` from the archive.org Stack Exchange mirror | CC BY-SA 4.0, with attribution to the posts | Question titles are weak-labelled for training. 200 of them were hand-checked for the test set. |
| [CLINC150](https://github.com/clinc/oos-eval) `data_full.json` | CC BY 3.0 | Out-of-scope examples, plus a few in-scope intents mapped to ours (`intent/src/clinc.py`) |
| The 160 "real" harness questions (90 Stack Exchange, 40 from the Hugging Face `its-myrto/fitness-question-answers` set, 30 from an mlfoundations set) | Stack Exchange CC BY-SA; the myrto set states **no licence** | External evaluation only. The texts and our hand labels are kept **outside the repo** for that reason. Their Stack Exchange ids are listed in `intent/labels/eval_leak_ids.txt` and removed from training. |
| Roboflow Universe: [south-indian-food-detection](https://universe.roboflow.com/bharani-1ucid/south-indian-food-detection) (bharani-1ucid) | Shown on its page. Record it here at download time. | Food-photo training crops (`food/src/coco_to_cls.py`). **Not downloaded yet.** |
| Roboflow Universe: [indian-food-txofy](https://universe.roboflow.com/microplastics-vypxl/indian-food-txofy) | Shown on its page. Record it here at download time. | Same. **Not downloaded yet.** |
| Roboflow Universe: [IndianFoodNet-30](https://universe.roboflow.com/indianfoodnet/indianfoodnet) (optional) | Shown on its page. Record it here at download time. | Same. **Not downloaded yet.** |
| [Open Images V7](https://storage.googleapis.com/openimages/web/index.html), validation split | Annotations CC BY 4.0. Images are listed as CC BY 2.0, each with its author. | `not_food` class (`food/src/fetch_not_food.py`). Author and licence of each photo are written to `_ATTRIBUTION.csv`. |
| ImageNet-pretrained MobileNetV3-Small weights (torchvision) | BSD-3-Clause (torchvision code and weights) | Starting point for food-photo v0 |
| The team's own meal photos (`data/raw/_test-own`) | Ours. Kept off the public repo. | The food gate's test set. Never used for training. |

Before training the food model, open each Roboflow dataset page you download and write its
licence and version into this table.
