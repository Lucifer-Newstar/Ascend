# Hunter stats (stats-v1)

The Status panel on Today shows five stats, each a 0-100 score **computed from your own
logs**. Nothing is allocated by hand and no model is involved, so a stat cannot be faked by
clicking and it is always explainable. `GET /game/stats` returns each value with its
formula and the numbers it used, and the panel's "Why?" button shows them.

Code: `services/sidecar/app/modules/gamification/stats.py` (`compute_stats` is pure and
unit-tested; `gather` reads the inputs). Window: the last 28 days unless stated.

| Stat | Formula | Inputs |
|---|---|---|
| **STR** Strength | the better of (a) earned steps in the strength skill trees (muscle-up, one-arm push-up, dips, pistol squat, nordic curl) ÷ their total, and (b) best weighted e1RM in 90 days ÷ body weight, where 2.0× = 100 | steps earned/total, best e1RM, body weight (latest weigh-in, else profile) |
| **AGI** Agility | earned steps in the skill trees (L-sit, handstand, front lever, back lever, planche, human flag, dragon flag) ÷ their total | steps earned/total |
| **END** Endurance | cardio + martial-arts minutes ÷ 600 | minutes in 28 days |
| **VIT** Vitality | ½ × check-in days ÷ 28 + ½ × average readiness ÷ 100 | check-in days, mean readiness |
| **INT** Discipline | ½ × days with a logged meal ÷ 28 + ½ × quest tasks completed ÷ issued | meal days, quest tasks |

Notes and limits:

- Entry steps of a skill tree start unlocked, so they are not counted as earned.
- The 2.0× body-weight scale for STR is **ASCEND's own scale choice**, not a population
  strength standard; it only maps a ratio to 0-100.
- The 600-minute END target is the WHO adult guideline of at least 150 minutes of moderate
  activity a week ([WHO fact sheet](https://www.who.int/news-room/fact-sheets/detail/physical-activity)),
  times four weeks.
- Scores are rounded to whole numbers (Python's `round`, so .5 rounds to even).
- These are motivation signals, not fitness tests; they are not validated against any
  external measure.
