# Awakening onboarding (v5)

First run is five short steps, each skippable, with nothing behind a wall:

1. **Name, units and body data** (age, sex, height, weight), entered in the chosen units.
2. **Focus** (strength, muscle, skills, fat loss), **calorie goal** (follows the focus until
   set by hand: fat loss → cut, muscle → bulk, otherwise maintain), activity level and
   training days per week (`settings.sessions_per_week`).
3. **Equipment checklist**: none, pull-up bar, rings, dumbbells, full gym. Saved on the
   profile (`profile.equipment`); editable later in Settings → Profile.
4. **Baseline test**: max strict push-ups, max pull-ups or a dead hang (only offered with a
   bar, rings or a gym), a plank hold, bodyweight squats in 60 s and today's weight. Built-in
   stopwatch and 60 s countdown. `POST /profile/baseline`.
5. **"[SYSTEM] You have been selected."**: rank and level, the starting calorie and protein
   estimates, and the first daily quest.

## What the baseline does

Each result is logged as one max-effort set (RPE 10) in a single finished session noted
"Baseline test". It goes through the normal set logger, so it earns XP (and so level and
rank), feeds the skill trees and the hunter stats exactly like any logged set. Nothing is
invented: a skipped test logs nothing, and 0 counts as skipped. The results are also kept on
the profile (`profile.baseline`). Most skill steps need two sessions, so a baseline usually
starts trees rather than unlocking steps.

## The equipment filter

`app/modules/workouts/equipment.py` maps the checklist to the library's equipment values:
body weight, none and mat always fit; a pull-up bar adds `bar`, rings add `rings`,
dumbbells add `dumbbell`; a full gym (or an empty checklist, meaning "not stated") removes
the filter. It is applied to:

- the daily quest's suggested exercise (`gamification.service._exercise_refs`);
- "Train this skill" items, both the step's criteria and the feeders
  (`skills.service.train`). When nothing fits, the reply says so.

Test: `tests/api/test_awakening.py::test_dumbbell_only_user_never_gets_a_barbell_quest_item`
checks 14 consecutive days of quests for a dumbbell-only profile.

Not filtered (by design): the exercise library and the logger, which still list everything,
so a user can log what they actually did anywhere.
