# Streaks, rest days and near goals (v1.3)

How ASCEND counts showing up, written for the viva and for anyone changing
`services/sidecar/app/modules/gamification/`. The design rules it follows are D2
(no loss aversion) and D3 (calm reminders) in [RULES_AND_BASELINE.md](../RULES_AND_BASELINE.md).

## What keeps the streak

| Day | Effect on the streak | Code |
|---|---|---|
| A training day: a finished workout or at least one logged set | +1 | `service.active_days` |
| A planned rest day of the program you follow | Neutral: the streak stays as it is | `service.planned_rest_days`, `streaks.compute_streak(rest_days=...)` |
| A missed day with a reason given by the next day | Kept as rest (counted in `excused`) | `streaks.compute_streak(reasons=...)` |
| A missed day without a reason | The streak starts again from the next training day | `streaks.compute_streak` |
| A meal, a weigh-in or a quest tick alone | Earns XP and quest progress, not the streak | review S2 |

The **best streak** never goes down and is shown beside the current one.

## Numbers that never go down

The summary (`GET /game/summary`) carries these next to the streak (`StreakOut`):

- `lifetime_sessions`: every training day so far.
- `next_milestone`: the next of 1, 3, 5, 10, 25, 50 and 100 sessions (`streaks.SESSION_MILESTONES`).
- `weeks_in_a_row` and `week_target`: weeks (Monday to Sunday, local time) that met the
  plan's training days, or beat the weekly boss. The current week counts once it is met and
  never breaks the run while it is still going (`streaks.weeks_in_a_row`).
- `rest_today`: today is a planned rest day, so Today shows no reminder.

`XpOut` adds display-only sub-ranks: `sub_rank` (E1, E2, E3 ... S at 10-level steps),
`next_sub_rank` and `next_sub_rank_level` (`formulas.sub_rank_for_level`). The XP formula
itself is unchanged.

On Today these appear as **Within reach** on the Hunter card; Progress opens with
**Sessions, all time**.

## Welcome back

The first session after at least one unplanned missed day pays **+25 XP** once per week
(`service.WELCOME_BACK_XP`, `service.welcome_back_due`, source `welcome_back`). If that
session stops counting (its sets are deleted), the bonus is reversed with it. The trainer's
feed says "Welcome back." and, when you gave one, repeats your reason without judging it.

## Unlocks that used to need a streak

| Item | Before v1.3 | From v1.3 |
|---|---|---|
| Crimson Gate theme | 7-day streak | 10 sessions |
| Ronin outfit | 7-day streak | 10 sessions |
| Focus Charm relic | 14-day streak | 25 sessions |
| Spear of Valor weapon | 30-day streak | 50 sessions |

A best streak that already met the old rule still unlocks the item, and stored unlocks are
never removed.

## Reminders

At most two a day, never on a planned rest day, no water reminder and no loss words
(`apps/desktop/src/lib/reminders.ts`, tested by the R6 block in `reminders.test.ts`). The
evening check, the monthly photo reminder and the weigh-in nudge are off until you turn them
on in Settings.

## Tests

- `services/sidecar/tests/unit/test_near_goals.py`: milestones, weeks in a row, sub-ranks.
- `services/sidecar/tests/api/test_v13_near_goals.py`: the summary fields and the Crimson unlock.
- `services/sidecar/tests/api/test_v13_welcome_back.py`: once a week, reversed with the session.
- `services/sidecar/tests/rules/test_rules.py`: the streak and undo rules (r1-r5).
- `apps/desktop/src/lib/reminders.test.ts` and `cosmetics.test.ts`.
