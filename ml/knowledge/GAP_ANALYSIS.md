# Knowledge-gap analysis (v1.4)

What real users ask about fitness, martial arts and meditation that ASCEND could not
answer, and what was added. Measured 2026-10-26 to 2026-10-27.

## Where the questions come from

The Stack Exchange data dumps on the archive.org mirror (CC BY-SA 4.0). The questions were
**only used to find what was missing**: no question or answer text is copied into the app,
the notes or the library. The extracted titles stay outside the repo, like the intent raw
data (see [../SOURCES.md](../SOURCES.md)).

| Site | Questions mined | Counted in the scan |
|---|---|---|
| fitness.stackexchange.com | 10,217 | 10,217 |
| martialarts.stackexchange.com | 2,307 | 2,307 |
| buddhism.stackexchange.com (meditation practice only) | 1,336 | 1,317 |
| health.stackexchange.com | 1,190 | 1,190 |
| sports.stackexchange.com | 389 | 389 |
| **Total** | **15,439** | **15,420** |

## Method

`knowledge/src/gap_scan.py` puts every title into a topic with keyword rules on the title
and tags (first match wins) and asks the knowledge base, with the intent model, for its
top passage. A question counts as **covered** when that passage passes the app's confidence
gate (score at least 12 and at least 40% of the query terms). This is a retrieval signal,
not a check that the answer is right: the hand-judged numbers are further down.

```
python knowledge/src/gap_scan.py --questions <folder with the *_questions.jsonl files>
```

## Coverage before and after

| Topic | Questions | Covered before (kb-v1) | Covered after (v1.4) |
|---|---|---|---|
| meditation | 1,343 | 5.0% | 27.3% |
| traditional martial arts | 1,178 | 14.2% | 23.3% |
| boxing / kickboxing / Muay Thai | 768 | 15.2% | 43.9% |
| breathing | 228 | 21.1% | 44.7% |
| yoga | 164 | 21.3% | 34.8% |
| supplements | 360 | 26.7% | 39.4% |
| injury and pain | 559 | 28.3% | 38.5% |
| cardio and running | 2,304 | 28.9% | 44.8% |
| gym and strength | 2,118 | 30.7% | 43.5% |
| mobility and flexibility | 616 | 31.2% | 43.5% |
| nutrition | 1,745 | 32.5% | 40.2% |
| calisthenics skills | 160 | 36.2% | 53.1% |
| sleep and recovery | 664 | 38.1% | 47.1% |
| other | 3,213 | 28.2% | 33.9% |
| **All** | **15,420** | **25.8%** (3,980) | **38.3%** (5,904) |

More questions now pass the gate. That is not the same as more right answers: on the
held-out gap questions below, the share of gated answers that were relevant went down.

## The gaps found, by specialist

* **Kai (cardio, martial arts).** No hook, uppercut, elbow, parry/block or kick-check drill;
  no switch kick or low kick; nothing on hand wraps, stance (orthodox or southpaw), shin
  conditioning, kicking higher, footwork, starting at home or what to expect in a first
  class. No interval cardio (run-walk, sprints, Tabata, HIIT), nothing on the talk test,
  easy runs, side stitches, shin splints, heat or swimming breathing.
* **Tara (mobility, recovery, meditation).** Only box breathing and three meditation rows;
  no 4-7-8, belly, alternate-nostril or humming breath; nothing on how to start meditating,
  a wandering mind, posture, or strong emotions during practice. Yoga poses only pigeon and
  sun salutation. No splits, hip, ankle, wrist or shoulder mobility, no desk-posture or
  neck-stiffness note, little on sleep, naps and soreness that lasts.
* **Dario (calisthenics).** No knee push-up (the first step for many beginners), Hindu
  push-up, archer or typewriter pull-up, toes-to-bar, wall walk, elbow lever, shrimp or
  Cossack squat; nothing on the first muscle-up, handstand, front lever, planche or L-sit
  progressions, or when to add weight.
* **Idris (gym).** No kettlebell swing, Pendlay row, landmine press or grip trainer; nothing
  on bracing and breathing, trap-bar vs straight-bar deadlifts, training with only
  dumbbells, or machines vs free weights.
* **Vera (nutrition).** Whey timing, mass gainers, caffeine and pre-workouts, beta-alanine,
  BCAAs, ashwagandha, electrolytes, multivitamins and protein-only diets had no note.
* **Library rows with no steps.** 20 rows had none, including Box Breathing,
  Shadowboxing, Pigeon Pose, Heavy Bag Rounds and Karate Kata.

## What was added

* **63 library entries** (`services/sidecar/app/modules/workouts/gap_fill_seed.py`,
  migration 0034): Dario 14, Idris 4, Kai 9 cardio and 9 martial-arts drills, Tara 19
  mobility and yoga and 8 breathing and meditation practices, each with steps, muscles,
  equipment, level and the specialist. Steps were written for the 20 rows that had none.
  Martial-arts drills are solo (air, bag or wall); anything with a partner says "only in a
  class with a coach". Breathing practices tell you to stop if you feel dizzy.
* **8 new note files, 125 new note passages** (`knowledge/notes/`): calisthenics skills,
  cardio and running, gym and strength, martial arts, meditation and breathing, mobility and
  yoga, sleep and recovery, supplements. Our own words; figures cite the guideline or
  position stand they come from (US Physical Activity Guidelines 2018, CDC, ISSN, NCCIH).
* **166 library passages**: every ASCEND-own library row with steps is now in the knowledge
  base (`lib:<coach>:<slug>`), so the coaching team knows whose area a passage is in.
* **Intent templates** for the new coaching topics (strikes, poses, breathing, skills, new
  moves and holds) in `intent/src/templates.py`; 33 regression questions in
  `knowledge/app_questions.yaml`; routing keywords in `trainer/team.py`.

The knowledge base grew from 1,473 to 1,779 passages (the 15 new food rows of the same
release add 15 food-table passages).

## Held-out gap questions

120 questions were drawn from the weak topics above (74 fitness, 19 martial arts, 11
sports, 9 buddhism, 7 health). 65 (the dev half) were read while writing the notes; 55 (the
test half) were only scored, after the notes were written. 15 of the test half are outside
the app's scope (for example Buddhist doctrine) and should get "no note". Their texts and
judgments stay outside the repo (CC BY-SA); the 74 Fitness ids are in
`intent/labels/gap_eval_ids.txt` and never reach intent training.

For each test question the top 3 passages of the old and the new build were judged
relevant or not by one rater (relevant = useful toward the answer). **Not double-checked.**

| Test half | kb-v1 | v1.4 |
|---|---|---|
| In scope (40): relevant passage first | 11 | 11 |
| In scope (40): relevant passage in the top 3 | 15 | 18 |
| In scope (40): answered at the gate | 13 | 19 |
| ...of which relevant | 6 (46%) | 7 (37%) |
| Out of scope (15): no note given | 14 | 13 |
| Routed to the expected specialist (55) | 31 | 34 |

So on new questions the top-3 improves a little and more questions get an answer, but the
first passage is often a note on a neighbouring topic. Keyword search is the limit: the
next step is better ranking (synonyms, a small re-ranker), not more notes.
