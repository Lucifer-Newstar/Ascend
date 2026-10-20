# Loophole and bug sweep (ASCEND v4, 2026-10-20)

Each finding has a fix and a test. XP rules changed under formula version `xp-v3` (decision D18). Old ledger rows keep their version.
Tests live in `services/sidecar/tests/api/test_loopholes.py` unless noted.

## Nits

| # | Finding | Fix | Test |
|---|---|---|---|
| N1 | Muscle map legend: "Ready to train" used a green dot, but the map pulses a ready muscle in its own status colour (often blue) | The key is now a neutral pulsing ring labelled "Ready to train (pulsing)" | visual check (dashboard screenshots) |
| N2 | Deload card read "e1RM down 3% or more on: no key lift" | Reads "No key lift has dropped 3% or more in e1RM", or "e1RM down 3% or more on Back Squat, Deadlift" | `tests/unit/test_deload.py` |
| N3 | Dashboard skeleton flashed for a few frames on every reload, and again on every return to the page | Last result cached for the session and painted at once; a first load shows the skeleton only after 250 ms | `useApi.test.tsx`, `Skeleton.test.tsx` |

## XP farming

| # | Loophole | Fix | Test |
|---|---|---|---|
| L1 | Delete a set and log it again: XP paid again (the ledger never subtracted) | Deleting a set appends negative rows cancelling its set and PR XP | `test_delete_then_relog_does_not_pay_twice` |
| L2 | Edit a set into a PR, or keep PR XP after editing a typo away | An edit never pays XP; if the set is no longer a PR, its PR XP is reversed | `test_pr_xp_rules_typo_jump_once_per_day_and_edits` |
| L3 | PR ladder: +0.5 kg every set paid 40 XP each time | PR XP at most once per exercise per day and 3 a day | same test |
| L4 | Absurd sets: a 500 kg typo paid PR XP | No PR XP for a jump of more than 25% over the previous best. The set and its PR flag still stand as data, so the user can fix the typo | same test |
| L5 | No diminishing returns: 200 easy sets of curls filled the daily cap | Set XP stops after 10 sets of one exercise or 40 sets a day | `test_set_xp_has_diminishing_returns` |
| L6 | 1-set "sessions" farmed the 20 XP session bonus; a workout left open for 3 h earned 0.5 XP a minute | Bonus needs 3 sets or 10 timed minutes; counted minutes are capped at 10 per set plus timed minutes; 2 paid sessions a day at most | `test_session_bonus_needs_real_work_and_caps_idle_minutes` |
| L7 | Delete sets from a finished session and keep its bonus | The bonus is reversed when the session drops below the minimum | `test_deleting_sets_from_a_finished_session_reverses_its_bonus` |
| L8 | Skill-step XP could be kept after deleting the sets that proved it | The unlock is revoked (with dependent steps) and its XP reversed | `tests/api/test_skills.py::test_deleting_the_proof_revokes_the_step_and_its_xp` |
| L9 | "Train this skill" could be pressed repeatedly to stack quest XP | Idempotent per exercise; at most 4 skill items a day | `tests/api/test_skills.py::test_train_adds_capped_idempotent_quest_items_that_complete` |

## Unrealistic inputs

| # | Loophole | Fix | Test |
|---|---|---|---|
| U1 | Holds accepted up to 6 h (a minutes/seconds typo) | Holds over 1 h are refused, both when logging and when editing; imports drop them with a warning | `test_unrealistic_holds_and_hold_edits` |
| U2 | Editing a hold could set reps to 40 | A hold's reps stay 1 | same test |
| U3 | Implausibly long holds on elite statics (front lever, planche, …) would unlock skills | Holds over 120 s on those are ignored for skill progress and flagged in the UI | `tests/unit/test_skill_engine.py::test_added_load_requirement_and_implausible_holds` |
| U4 | Bodyweight moves defaulted to the logger's 40 kg barbell weight, so a pull-up logged as weighted | Bodyweight and calisthenics moves start at 0 kg, labelled "Added load" | `Workout.test.tsx` |

## Time zones and midnight

| # | Loophole | Fix | Test |
|---|---|---|---|
| T1 | Quest progress counted sets by the session's start day: sets after midnight fed yesterday's quest | Counted by each set's own date | `test_sets_after_midnight_count_for_the_new_day` |
| T2 | A wall clock jumping back (time-zone change) could put a set before the previous one | Sets in a session never go earlier than the set before | `test_a_clock_jumping_back_keeps_sets_in_order` |
| T3 | Streaks use calendar days of the local clock; a session crossing midnight counts for the day it started | Kept as designed (one session, one day) and documented. A deliberately changed system clock is out of scope for an offline app | — |

## Quests

| # | Loophole | Fix | Test |
|---|---|---|---|
| Q1 | Quest suggestions drew from all 942 library entries, including obscure imports | Suggestions come from ASCEND's core list, your own exercises and anything you have logged | `test_every_training_quest_can_be_completed` |
| Q2 | Could a quest be impossible to complete? | Property test: over 14 generated days, logging the suggested exercise for the target number of sets always completes the item | same test |

## Custom exercises, duplicates and imports

| # | Loophole | Fix | Test |
|---|---|---|---|
| C1 | One custom exercise with every muscle as primary would tick every muscle quest per set | At most 3 primary muscles | `test_custom_exercises_cannot_game_muscle_quests_or_clash` |
| C2 | A custom cardio exercise measured in reps (or a lift measured in time) broke XP and load maths | Measure must match section; proposals are made consistent before review | same test |
| C3 | Duplicate exercises: a custom "Pull ups", or a custom alias "Pull-up" | Names and aliases are checked against the library (normalised) → 409 | same test; `test_custom_exercises.py` |
| C4 | Removing a custom exercise would orphan its sets and PRs | Removal archives it; sets and stats stay | `test_custom_exercises.py::test_validation_and_archive` |
| I1 | Importing a session that was also logged in ASCEND counted it twice | A workout starting within 30 min of an app-logged one with a shared exercise is skipped as a duplicate | `test_import_skips_future_dates_and_sessions_already_logged` |
| I2 | Future-dated rows were imported | Skipped with a warning | same test |
| I3 | Imported history could unlock skills and pay XP | Imports can unlock skill steps but pay no XP | `tests/api/test_skills.py::test_imported_history_unlocks_without_xp` |

## Other bugs found on the way

- The "Log it" hand-off from the gallery or a skill opened the logger on Gym. React's development double render consumed the pending exercise. Fixed by peeking in the initializer and clearing in an effect.
- Matcher alias "plank" still pointed at the old "Plank (60 s = 1 set)" name after the rename. Imported planks also dropped their seconds.
- History showed holds as clock times; they now read "20 s hold +5 kg".
