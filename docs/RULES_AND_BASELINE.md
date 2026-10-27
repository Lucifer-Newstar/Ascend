# ASCEND rules and baseline

> Owner: **Navin**. Started 2026-10-25 for v1.3. This page is the yardstick for every new
> feature: the design rules come from the v1.3 review (its §4, §5.3 and §6) and the decisions
> in the v1.3 plan; the technical rules and the baseline numbers are what CI and the wave
> reports check against.
>
> **How to use it.** Before a feature is built, read the design rules. If the feature needs to
> bend one, say so in its pull request ("DESIGN CHECK") and ask Navin; do not change the rule
> quietly. Every report and release note has a "RULES CHECK" line: the rules broken or the
> baselines that got worse, or "none".

## 1. Design rules (how a feature has to be designed)

| # | Rule | Why (source) |
|---|---|---|
| D1 | **Rewards are cosmetic and earned by effort.** XP, ranks, themes and wardrobe items come from training (sessions, weeks, boss clears), never from money, chance or logging for its own sake. No loot boxes, no random drops, nothing that makes training easier. | Review §4.1/§4.3 (gamification helps when it rewards the target behaviour; gambling-like mechanics are on the "do not add" list); S2 "only training keeps the streak". |
| D2 | **No loss aversion, no FOMO.** Copy never threatens a loss ("your streak ends at midnight"). A missed week never locks a seasonal or timed item away for good: there is always a catch-up path or a later re-run. | Review §4.2/§4.3 and decision 3 (calm reminders); Navin 2026-10-25 (catch-up for weekly, monthly, yearly and seasonal rewards). |
| D3 | **Progress is always visible, with a near goal.** The next unlock, the next milestone or the next sub-rank is on screen; two numbers never reset (lifetime sessions, best streak). | Review §2.4 and item 1.6 (near goals), S5. |
| D4 | **Autonomy: the user decides, the trainer proposes.** Every change the trainer or an AI makes is a card the user confirms, and can undo. Optional features stay optional. | Review §4.2 (self-determination), plan §B, ADR-0005. |
| D5 | **Calm notifications.** At most two reminders a day (one, plus an optional evening "not done yet"), none on a planned rest day, opt-in tray and start-with-Windows. | Review decision 2 and 3, item 1.4. |
| D6 | **No spoilers, but clear "how to unlock".** Locked bosses and items show as a silhouette with what unlocks them, never their art or name in advance. | Navin 2026-10-25 (boss ladder in Profile). |
| D7 | **Readable in every theme.** Text meets WCAG AA (4.5:1) on every surface of every theme; art sits behind a scrim. | UI-1 (v1.2) and Navin's v1.3 brief ("themes must never make text unreadable"). |
| D8 | **Motion is optional.** "Reduce motion" (and the OS setting) turns every reveal, cutscene and animation into a still frame. | Accessibility guide (docs/development/accessibility.md). |
| D9 | **Offline first.** Everything works with no internet and with the local AI off (the default). The one online feature is opt-in per use. | Project brief, ADR-0004/0005. |
| D10 | **Viva-safe and kind.** Trainers are adults in gym wear; no comments on bodies or body fat; under-18 users never see calorie numbers; no medical claims. | Plan §C, review decision 6, the coach guard. |
| D11 | **Fewer screens, not more.** A new feature joins an existing page unless it clearly needs its own; the core loop (plan → train → see progress) stays the shortest path. | Review §5.1 (cuts) and decision 5. |

## 2. Technical rules (checked)

"Checked by" names the test or script that fails when the rule breaks. "Manual" means a
person checks it in review until a test exists.

| # | Rule | Checked by |
|---|---|---|
| R1 | Only training keeps the streak: a finished workout or at least one logged set (meals, weigh-ins, ticks earn XP only). | `services/sidecar/tests/rules/test_rules.py::test_r1_*`, `tests/api/test_v13_streak.py` |
| R2 | Days the followed program does not train are neutral: no reason needed, never a break. | `test_rules.py::test_r2_*`, `test_v13_streak.py` |
| R3 | The trainer never writes before Confirm, and works with the AI off. | `test_rules.py::test_r3_*`, the trainer battery (B1) runs with the AI off |
| R4 | Nothing erases everything from a typed "yes"; "remove all meals" is not an erase; erase needs its word typed. | `test_rules.py::test_r4_*` |
| R5 | Every trainer change (log, plan, settings, kit, profile) can be undone. | `test_rules.py::test_r5_*`, `tests/api/test_v13_edits.py` |
| R6 | Reminders: at most 2 a day, none on a planned rest day, no loss or guilt words. | `apps/desktop/src/lib/reminders.test.ts` (rules block) |
| R7 | Every text token is at least 4.5:1 on every surface in every theme. | `apps/desktop/src/lib/tokens.test.ts` |
| R8 | No phone numbers, tokens or keys in the repo. | `scripts/check_rules.py` (CI, docs job) |
| R9 | The team is the author: no assistant credited as author; the README keeps "Parts of this codebase were written with AI assistance." | `scripts/check_rules.py` |
| R10 | Scan meal only suggests (top 3) and never logs on its own; it hides itself with no gated model. | Manual until the ML branch (`feat/ml-models`) lands with its tests |
| R11 | No accuracy is claimed for a model that has not passed its gate on the team's own test set. | Manual (model cards, release notes) |
| R12 | Under 18: calories hidden everywhere; no body or body-fat comments anywhere. | `tests/api/test_profile.py`, coach guard tests; copy is manual |
| R13 | Offline: only "online lookup" contacts the internet, off by default. | `tests/api/test_online_research.py` |
| R14 | Dates and times use the local system clock and time zone (streaks, weekly and monthly resets, seasons, recap). | `tests/api/test_v14_local_dates.py` (fake local clock over midnight), `lib/localDate.test.ts` (Asia/Kolkata, and no `toISOString()` dates in the app's code) |
| R15 | Cosmetics show on the avatar only when equipped (and earned). | `equippedGear()` in `lib/cosmetics.ts`; `pages/Profile.test.tsx` ("wears only what is equipped and unlocked") |
| R18 | No spoilers: Profile shows cleared bosses only, the next one as "???"; locked cosmetics are silhouettes; no unlock rule names a seasonal boss. | `pages/Profile.test.tsx` (trophy shelf, Wardrobe), `lib/cosmetics.test.ts` ("no spoilers") |
| R19 | Every time-bound reward (seasonal drop, monthly or yearly clear) has a catch-up total. | `lib/cosmetics.test.ts` ("gives every time-bound unlock a catch-up total") |
| R16 | Reduce motion is honoured by every animation. | `lib/motion.test.tsx` and the component tests that switch it on |
| R17 | History is real: linear, no merge, empty or backdated commits; each commit under its owner; headers ≤ 120 characters. | commitlint in CI; review |

## 3. Baseline (measured)

Measured on `feat/kb-gap-fill` on 2026-10-27 (the code as of `ddbfa72`; the commits after it on
that branch change docs only). The previous baseline was measured on `feat/v13-trainer-actions`
at `81bfb45` (2026-10-25) and is kept in the "was" notes. A later branch may raise a number; it
may not lower B1, B3 or B4, or raise B2 or the eslint errors, without saying so in its RULES
CHECK line.

| # | What | Value | How measured |
|---|---|---|---|
| B1 | Trainer battery passes (352 messages, AI off) | **260** (unchanged; was 251 of 343 before the nine plan-builder messages, `feat/v14-plan-builder`) | `cd services/sidecar && uv run python -m eval.trainer_chat` |
| B2 | Trainer battery fails | **1** ("follow the 5 day split": no 5-day program) | same |
| B2b | Battery rows a person reads | 91 | same |
| B3 | Sidecar tests | **1200 passed** (was 1084) | `uv run pytest` |
| B4 | Desktop tests | **612 passed** (92 files; was 545 in 79) | `npm test` |
| B5 | eslint | 0 errors, 22 warnings | `npm run lint` |
| B6 | Alembic | one head, `0035` (was `0032`) | `uv run alembic heads` |
| B7 | API contract | 146 implemented operations match 18 contracts (was 137 and 16) | `make contracts` |
| B8 | 160 real fitness questions (dataset batch) | 19 relevant answers, 54 unrelated notes, 87 honest "no note" | hand-graded on `feat/v13-fixes` (wave 1); not re-graded since. The ML cards report later, separate measures on the same questions ([ml/README.md](../ml/README.md)) |
| B9 | Renderer build | main chunk 345 kB (106 kB gzip); `dist` 23 MB with the exercise images (was 336 kB, 103 kB gzip) | `npm run build` |
| B10 | Windows installer size | not measured yet (needs a Windows build) | `npm run dist:win` on Windows |

B1 and B2 are enforced by `test_rules.py::test_b1_*`. B3 to B7 are checked by CI running the
suites themselves; the counts are recorded here so a drop is visible in review.

## 4. Changing a rule

A rule changes only with Navin's OK, in the same pull request that needs it: update the row,
add the date and the reason, and update its test. A baseline moves up when a branch improves
it (write the new number and the commit it was measured on).
