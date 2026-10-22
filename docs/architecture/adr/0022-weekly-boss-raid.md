# ADR-0022: Weekly Boss Raid (boss-v1)

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Navin Jairam M (lead)

## Context

The owner asked for one weekly goal that makes training feel like a game without adding
another reward channel to check. The engagement research (`docs/research/v8-gamified-engagement.md`)
supports an adaptive, specific weekly goal that rewards the training itself, and warns
against loss mechanics and rewards for simply showing up. For the same reason v8 drops
achievements, login/check-in rewards and reminder notifications; the boss title is the
only title source.

## Decision

1. **One boss a week** (`gamification/boss.py`, `ALGO_VERSION = "boss-v1"`). It appears on
   Monday (the first time the app asks that week) and lasts until Sunday. The boss and
   its title come from a fixed rotation of 12 original names, chosen by the week.
2. **HP is a week of your own training**, fixed when the boss appears:
   - the working sets of the program you follow (programs-v1), halved in a deload week;
   - else the median number of training sets per week over the 4 weeks before;
   - else 20 (a starter boss);
   - clamped to 12-150.
3. **Damage is counted, not stored:** each set logged that week in a training section (gym,
   calisthenics, martial arts, cardio) deals 1. Mobility and meditation do not. Editing or
   deleting a set changes the damage like every other number.
4. **Beaten at 0 HP by Sunday:** +150 XP once, outside the daily XP cap (it is at most one
   grant a week), and the boss's title on the Hunter profile. The defeat time is the time
   of the set that emptied the HP bar. If deleted sets bring the boss back above 0 HP, the
   bonus is reversed in the append-only XP ledger and the title is removed.
5. **Missed: nothing happens.** No penalty, no lost streak, no lost XP. Next Monday brings a
   new boss sized from your recent weeks.
6. **Storage:** `boss_raids` (migration 0019), one row per week with the boss, HP, where the
   HP came from and when it was beaten. **API** (tag `gamification`): `GET /game/boss`,
   `GET /game/titles`.

## Consequences

- The same logs always give the same boss, HP and outcome; unit tests cover the rotation,
  every HP rule, the defeat set, and the API covers the bonus, the reversal and a missed week.
- A whole number per set is easy to read on an HP bar. It does not weight hard sets above
  easy ones; recovery and progression already do that.
- The HP rules and the 150 XP bonus are design choices, not tuned on data. The research
  document marks them [design; unverified tuning].
