# Model card: ASCEND intent router 1.1.0 (intent-v1.4)

**What it does.** It decides what a trainer-chat message is: one of 22 intents, such as
`log_set`, `log_meal`, `nutrition_question`, `injury_pain` or `out_of_scope`. It never
reads numbers or food names out of a message; the rule parser does that.

**Where it runs.** In the sidecar, on the CPU, with the standard library only
(`services/sidecar/app/modules/ml/intent_runtime.py`). It takes about 1 ms per message (0.8 ms measured on the 160 questions). The
file is `assets/intent_model.json.gz` (734 KB) and is checked against
`intent-manifest.json` by SHA-256. Set `ASCEND_INTENT_MODEL=off` to turn it off.

**How the app uses it** (`trainer/ml_route.py`):
1. Rules that are sure about a message keep it.
2. The model is asked only when the rules found nothing or only a weak help-note match.
3. The app follows the model only at a confidence of **0.55** or more; below that, the
   rules answer.

**Model.** TF-IDF on word 1–2-grams and character 2–5-grams, then multinomial logistic
regression (scikit-learn, C=10, class_weight balanced; C chosen on val from {1, 4, 10}).
Coefficients below 0.02 are pruned and the rest rounded to 3 decimals. The pruned runtime
agrees with scikit-learn on 99.87% of 5,483 texts (the export gate needs 99.5%). Training
takes about 1 minute on a laptop CPU and is logged to MLflow (experiment `ascend-intent`).

**Data.** See [DATA_CARD.md](DATA_CARD.md): weak-labelled Stack Exchange titles, templated
Tanglish/Hinglish commands with typos, and CLINC150.

## Results (1.1.0 measured 2026-10-27, held-out data only)

1.1.0 is 1.0.0 retrained with the v1.4 gap-fill templates (strikes, yoga poses, breathing,
calisthenics skills, new moves; see `knowledge/GAP_ANALYSIS.md`). Same recipe and gate.

| Test set | n | 1.1.0 accuracy | Macro-F1 | 1.0.0 accuracy | Notes (1.1.0) |
|---|---|---|---|---|---|
| Held-out templates | 580 | 0.805 | 0.809 | 0.816 | At ≥0.55: 75% answered, 93% of those correct. |
| CLINC150 test | 2,463 | 0.875 | 0.864 | 0.877 | Out-of-scope recall 0.869 (1.0.0: 0.871) |
| Stack Exchange, hand-labelled | 200 | 0.775 | 0.602 | 0.755 | Route accuracy 0.960 (1.0.0: 0.955) |
| **160 real questions** (external) | 160 | **0.738** | **0.376** | 0.713 | Route accuracy 0.938 (1.0.0: 0.944). At ≥0.55: 68.8% answered, 78.2% of those correct. |
| 343 app-style messages | 329 | 0.915 | 0.838 | 0.918 | Written by the test author, **not real users** |

Real questions and hand-labelled titles improved; templates, CLINC and app-style messages
moved by one to three hundredths, within what a retrain changes. One fewer real question is
routed to the right handler.

Gate (`params.yaml` `intent.gate`): templates macro-F1 ≥ 0.80, hand-labelled SE accuracy ≥
0.60, out-of-scope recall ≥ 0.85, runtime parity ≥ 0.995. **It passes.**

How the external numbers were measured: the 160 questions (90 Stack Exchange, 40 myrto,
30 mlfoundations) were labelled by hand by one person, before the model was evaluated on
them. Labels: training 93, nutrition 31, how-to 21, injury 9, plan 4, out-of-scope 1,
motivation 1. Macro-F1 is low because several of those classes have 1 to 9 examples, and
the model confuses how-to with training questions (both go to the knowledge base, so the
route is still right). The labels and texts stay outside the repo because the myrto set
has no licence. Rerun with `python intent/src/evaluate_intent.py --external <dir>`.

## Limits

* No real ASCEND user messages were used. Expect lower accuracy on very short or mixed-
  language messages that the templates do not cover.
* Weak training labels are about 83% right.
* Out-of-scope recall is 0.87, so about 1 unrelated message in 8 is taken as fitness. The
  chat then tries the knowledge base, which only answers above its own score floor.
* It is a router, not a safety system. Pain messages get the "see a doctor or
  physiotherapist" line because of the route, and the model does not judge severity.
