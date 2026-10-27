# Card: ASCEND knowledge base and retrieval (kb-v1.4)

**What it is.** 1,779 short passages, each with its source, licence and place (PDF page,
exercise id, food), searched by BM25 in the sidecar (`app/modules/ml/knowledge.py`,
standard library only, about 2 ms per query on this corpus). The AI tab answers from the top passage and
shows its source. When the local AI is on, the top two passages are sent to it as context
and its numbers are checked against them.

| Source | Passages | Licence |
|---|---|---|
| free-exercise-db (exercise steps) | 871 | Unlicense |
| Physical Activity Guidelines for Americans 2018 | 306 | Public domain (US gov) |
| ASCEND food table (portion values) | 203 | MIT |
| ASCEND team notes | 166 | MIT |
| ASCEND library entries with steps (v1.4) | 166 | MIT |
| USDA FoodData Central SR Legacy (per 100 g) | 61 | CC0 |
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

## v1.4 gap fill (measured 2026-10-27)

15,439 real questions from five Stack Exchange sites showed which topics the base could not
answer (meditation, martial arts, breathing, yoga, interval cardio, supplements). v1.4 adds
125 note passages, 166 library passages (`lib:<coach>:<slug>`, so the coaching team knows
the area) and 15 food rows. Details and the per-topic table: [GAP_ANALYSIS.md](GAP_ANALYSIS.md).

| Measure | kb-v1 | v1.4 |
|---|---|---|
| Real questions, odd half (80): relevant passage first | 28 | **31** |
| Real questions, odd half (80): relevant passage in the top 3 | 38 | **40** |
| Real questions, odd half: answered at the gate / of which relevant | 30 / 17 | 41 / 22 |
| Held-out gap questions (40 in scope): relevant first | 11 | 11 |
| Held-out gap questions (40 in scope): relevant in the top 3 | 15 | **18** |
| Held-out gap questions: answered at the gate / of which relevant | 13 / 6 | 19 / 7 |
| Held-out gap questions out of scope (15): "no note" | 14 | 13 |
| App-style questions (49, top 3) | 16 / 49 | **49 / 49** |
| Stack Exchange titles passing the gate (15,420) | 25.8% | 38.3% |

Judged per question **and** passage (`kb_passage_judgments.json`, outside the repo), so each
build is scored on its own ranking. The kb-v1 column matches the frozen kb-v1 marks on all
80 real questions. One rater, not double-checked: treat the v1.4 numbers as unverified.
The honest reading: more questions get an answer and the top 3 is a bit better, but on the
new questions the first passage is often a neighbouring topic, so precision at the gate did
not improve. The app-style set grew from 16 to 49 questions (33 new gap topics); the gate
(hit@3 ≥ 0.9) still applies.

```
python knowledge/src/evaluate_kb.py --external <dir>                       # v1.4
python knowledge/src/evaluate_kb.py --external <dir> --build <old build> --intent-model <old model> --out before.json
```

## How good was kb-v1 (measured 2026-10-25)

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
