# Data card: trainer-chat intent dataset (intent-v1.4)

Built by `intent/src/build_dataset.py` (DVC stage `intent_data`, seed 42). It covers the 22
intents in `intents.yaml`.

| Split | Rows | Where the rows come from |
|---|---|---|
| train | 8,383 | 4,853 weak-labelled Stack Exchange titles, 1,929 templated app commands, 1,601 CLINC150 |
| val | 2,240 | 541 weak SE, 220 templates, 1,479 CLINC150 |
| test_templates | 580 | Templated commands from templates **held out of training** (about a quarter of templates, chosen by crc32) |
| test_se_hand | 200 | Stack Exchange titles, **labelled by hand** |
| test_clinc | 2,463 | CLINC150 test: 2,224 out-of-scope plus mapped in-scope intents |

## How the labels were made (disclosed)

* **Weak labels.** Stack Exchange titles are labelled by keyword and tag rules in
  `intent/src/weak_label.py`, not by people. On the 200 hand-checked titles these rules agree
  with the hand label 166/200 times (83%), so roughly 1 training title in 6 is mislabelled.
* **Hand-checked rows.** `labels/se_handchecked.csv` holds 200 titles drawn with seed 7 and
  labelled by one team member. Its `hand_label` column marks them. They are test-only and
  are never trained on.
* **Templates.** `intent/src/templates.py` generates app commands ("log 3 sets of 10
  pushups", "naan 2 chapati saapten", "bench 60 x 5 pannen") with Tamil-English (Tanglish)
  and Hindi-English (Hinglish) fillers, number words, and keyboard typos (dropped, swapped
  or doubled letters). Whole templates are held out for the test split, so the test is not
  the same sentences with new numbers.
* **CLINC150.** Banking, travel, weather and other out-of-scope requests teach the model
  to say "not mine". A few CLINC intents are mapped to ours (greeting, thanks, help, cancel,
  nutrition). The mapping is in `intent/src/clinc.py`, as `MAPPED` and `DROPPED`.

## Leak rules

* The 200 hand-checked ids are removed from the weak pool.
* 91 Stack Exchange ids whose title or opening matches one of the 160 external evaluation
  questions are listed in `labels/eval_leak_ids.txt` and removed from training.
* v1.4: the 74 Fitness Stack Exchange ids of the held-out gap questions
  (`labels/gap_eval_ids.txt`, see `knowledge/GAP_ANALYSIS.md`) are removed from training too.
* Duplicates are removed after normalising case, punctuation and spacing. The test
  template families never reach training.

## Limits

* The real users are Indian students typing short commands. Most training text is forum
  titles and generated commands. No message from a real ASCEND user was used.
* Label balance follows the sources: `training_question` has 2,334 train rows and
  `erase_data` has 49 (class weights are balanced).
* Out-of-scope recall on the hand-checked Stack Exchange set is meaningless (1 row).
* Licences: Stack Exchange text is CC BY-SA 4.0 and CLINC150 is CC BY 3.0 (see
  [../SOURCES.md](../SOURCES.md)). The dataset files are DVC outputs and are not committed.
