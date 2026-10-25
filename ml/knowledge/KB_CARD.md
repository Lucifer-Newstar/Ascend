# Card: ASCEND knowledge base and retrieval (kb-v1)

**What it is.** 1,473 short passages, each with its source, licence and place (PDF page,
exercise id, food), searched by BM25 in the sidecar (`app/modules/ml/knowledge.py`,
standard library only, about 2 ms per query on this corpus). The AI tab answers from the top passage and
shows its source. When the local AI is on, the top two passages are sent to it as context
and its numbers are checked against them.

| Source | Passages | Licence |
|---|---|---|
| free-exercise-db (exercise steps) | 871 | Unlicense |
| Physical Activity Guidelines for Americans 2018 | 306 | Public domain (US gov) |
| ASCEND food table (portion values) | 188 | MIT |
| USDA FoodData Central SR Legacy (per 100 g) | 61 | CC0 |
| ASCEND team notes | 41 | MIT |
| WHO 2020 guidance, our own summary | 6 | MIT (our words) |

Built by `knowledge/src/build_corpus.py` (DVC `kb_build`), checked by `evaluate_kb.py`
(`kb_evaluate`), and copied into the app by `knowledge/src/publish.py`. Full licences are
in [../SOURCES.md](../SOURCES.md).

**Retrieval.** BM25 (k1 1.2, b 0.75) with stop words, plural and compound folding and a few
fitness aliases. Two additions:
* A long forum post is cut down to its question sentences before searching.
* Each source gets a weight from the intent model's label. Notes lead; food tables count
  only for food questions; exercise steps count mostly for how-to questions.

A passage is shown only when its score is ≥ 12 **and** it contains ≥ 40% of the query's
terms. Otherwise the trainer says it has no note on that.

## How good is it (measured 2026-10-25)

**Real questions, judged by hand.** The 160 external questions were split by index. The
even half (80) was used to tune the source weights and the question-focus rule, to add two
notes (building muscle, intermittent fasting) and to retitle one (a safe rate of weight
change). The odd half (80) was **only** judged, once, after tuning. For each question one person marked
the top 3 passages relevant or not (relevant = useful toward the answer).

| Odd half (80 questions) | Count |
|---|---|
| A relevant passage ranked first | **28 / 80 (35%)** |
| A relevant passage in the top 3 | **38 / 80 (48%)** |
| Answered at the gate (score ≥ 12, coverage ≥ 0.4) | 30 / 80 |
| …of which the first passage was relevant | 17 / 30 (57%) |

The gate thresholds were picked by looking at a precision table on this same half, so
the 17/30 is optimistic. Many of these questions are long Stack Exchange posts on topics
the corpus does not cover (tabata, beta-alanine, boxing bags, body-fat measurement). The
honest summary: it helps with about a third of real forum questions and says "no note"
for most of the rest.

**App-style questions.** On 16 questions written by the team (`app_questions.yaml`, for
example "protein in idli", "is creatine safe", "how to do a plank"), the expected passage
is in the top 3 for **16 / 16**. This is the regression gate (≥ 0.9) and guards against
breaking retrieval. It does not measure quality on real users.

The hand judgments are in a file outside the repo, together with the question texts (see
SOURCES.md about the myrto licence). Rerun with
`python knowledge/src/evaluate_kb.py --external <dir>`.

## Limits

* It is keyword search, so synonyms it does not know are missed.
* The team notes are general guidance, **not reviewed by a medical professional**. Pain
  questions always get a "stop and see a doctor or physiotherapist" line first.
* Food values: USDA rows are per 100 g of the raw or prepared item named; food-table rows
  are rounded household portions. They are approximate.
* English only. Tanglish questions match only through the words they share with English.
