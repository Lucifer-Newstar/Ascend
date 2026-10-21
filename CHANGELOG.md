# Changelog

All notable changes to ASCEND. Versions follow [Semantic Versioning](https://semver.org/);
entries are grouped from Conventional Commits and written for users first.
Formula and model versions are listed where a number you see could change.

## [Unreleased]

### Added (v7 workout programs)
- **Workout programs** (`programs-v1`, ADR-0020): full body 3 days, upper/lower 4 days, push/pull/legs 6 days, and home full body 3 days (dumbbells and a pull-up bar).
  - The **Program card** on Train shows the next session: each exercise with your progression target, using the program's sets (halved in a deload week), and the sets already logged today. Click an exercise to log it.
  - A chooser lets you follow, change or stop a program, and says when a program needs equipment you didn't list at setup.
- **The plan reads your log.** A finished gym workout that trains at least half of a program day counts as that day. A missed day shifts the plan instead of skipping a session, and imported workouts count too. Nothing needs to be started or ticked off.
- **API:** `GET /plans/programs`, `GET/PUT/DELETE /plans/current`. This implements the planned `/plans/current` in `workouts.yaml`; `PlanOut` replaces the placeholder schema. Migration 0016 adds `plan_enrollments`.
- **Demo data** follows the push/pull/legs program.

### Added (v7 diet engines)
- **Adaptive TDEE** (`tdee-v1`, ADR-0018).
  - A Kalman filter on trend weight and expenditure that learns your real energy needs from weigh-ins and logged meals.
  - It starts at the Mifflin-St Jeor estimate with a ±450 kcal range. Missing days widen the range instead of breaking it, and days under 800 kcal count as partly logged.
  - Fuel's energy card shows what you burn as a range, this week's target and where it comes from, meal and weigh-in completeness, the reason the target held or moved, the 8-week estimate with its band, and a "Why?".
- **Adaptive weekly target.** Changes only on Mondays, after a week with 6 logged days and 4 weigh-ins, by at most 150 kcal. Missing a day never moves it.
  - Once set, it becomes the day's calorie target in Fuel and on Today's ring, and Settings shows it beside the formula estimate. `DayLog.kcal_target_source` says whether the target is `formula` or `adaptive`.
  - Before that, the target is exactly the profile's Mifflin-St Jeor value.
- **Weekly diet insights** (`insights-v1`, ADR-0019).
  - Six fixed rules over the last 7 complete days: intake vs target, protein, weekend vs weekday, weight trend vs goal, adaptive vs formula, and logging gaps.
  - Progress shows up to three findings, each with a "Why?", and a "Rules checked" list.
  - The trend rule uses the slope of your weigh-ins and its error, so one heavy morning does not trigger it.
- **API:** `GET /intelligence/tdee`, `GET /intelligence/insights`, and their `.../explanation` endpoints, where the local model may phrase the sentence behind the coach guard.
- **Evaluation** (`docs/ai/evaluation.md` §5). 100 synthetic users × 120 days, with honest and under-reporting logs, plus 300 user-weeks with injected patterns.
  - Median TDEE error at day 56: 82.8 kcal (formula: 194.7).
  - Limits: only 57% of users are within 150 kcal on day 28, and the trend insight's precision is 0.397.
  - Latency on a one-year history: tdee-v1 takes 3.08 ms.
- **Demo data.** `seed_demo` now adds 10 weeks of meals and weigh-ins before the detailed fortnight, so the adaptive estimate has history to learn from.

### Changed (v7 layouts)
- **Progress, Fuel, Coach, History, Import & export and Settings** now use the same 12-column layout as Today, Train and Skills (spec §8.4).
  - **Progress:** a KPI strip (trend weight, goal ETA, this week, PRs in 30 days), estimated 1RM or best hold per key movement, weekly sets per muscle against its band, and a PR timeline.
  - **Fuel:** a KPI strip (calories, protein, left or over, meals), today's intake and meals beside the adaptive TDEE card, and one meal-builder card with the food table and the plate side by side.
  - **Coach:** the chat at a fixed height beside the weekly review, the deload check and a System log of the engines' notices.
  - **History:** range KPIs, a training/meal-day filter, 30 or 90 days, an activity calendar that jumps to a day, and sessions by source.
  - **Import & export:** a choose → check → imported step strip; **Settings:** a sticky section index.
- Every card on these screens shows loading, error and empty states the same way (one `Panel` component), and cards rise in with a short stagger that Reduce motion turns off. No API contract changed.

### Added (v6 intelligence layer)
- **Recovery engine v2** (`recovery-v2`, ADR-0014).
  - Per-muscle readiness for all 19 regions. A set's dose counts its effort (reps in reserve from RPE, else from your e1RM), so an easy set loads a muscle less than a set to failure.
  - Holds count by seconds: a 12 s hold is 0.4 of a set, where it used to be a whole set.
  - Today's check-in (sleep, and soreness on muscles trained in the last 72 h) makes the same fatigue count for up to 45 % more.
  - Your history is re-scored once by migration 0014; the downgrade restores load-v1.
- **Personal recovery factors** (`recovery-k-v1`).
  - One factor per muscle group, learned from how your performance follows fatigue. It starts at the population value and moves only with evidence, shown with a 90 % interval.
  - Refitted after every finished workout.
  - The muscle drill-down shows **your readiness next to the population's** with a "Why?".
- **Progression engine** (`prog-v1`, ADR-0015).
  - The logger shows a **suggested next target**: sets × reps (or seconds) @ load and RPE, what changed (+2.5 kg, +1 rep, hold, reset) and a one-line reason.
  - **Use it** fills the inputs. **Keep mine** keeps your own numbers for 7 days (FT-1).
  - **How it decides:** double progression in your rep zone, equipment-aware increments (never more than 10 % at once), RPE autoregulation and e1RM tracking.
  - **When it holds back:** no increase while the trained muscles are under 40 % recovered; half the sets at RPE 7 in a deload week.
  - Calisthenics targets follow the open skill-tree criterion they feed.
- **Stalled lifts.** No rep record in 3 sessions is flagged, and the lift gets a 10 % reset. Two stalled lifts are a new deload signal (`deload-v2`, still two signals needed).
- **Explanations** (ADR-0016).
  - Every engine number has a "Why?" with the formula and every input.
  - With AI on, the local model may phrase the reason in one sentence. That sentence is shown only if every number in it is checked against the engine's facts (the coach guard); otherwise you see the template.
- **The System speaks, rarely.** Three notices, each shown once: **Deload advised**, **Target raised** after the session that earned it, and **Muscle recovered** when today's quest trains a muscle that is ready again.
- **Evaluation** (ADR-0017, `docs/ai/evaluation.md`). A seeded synthetic-user simulator compares both engines with baselines. It covers calibration and correlation against simulated ground truth, hit rate and over/undershoot, stall precision and recall, and latency on a one-year history. It also states where the engines are weak: stall precision is low (0.113, recall 0.62), every result is on synthetic users only, the recovery correlation is partly circular because the simulator shares the engine's model family, and real local-model phrasing is unverified. Rerunning the recovery and progression evaluations reproduces the committed JSON exactly.
- **API:** `GET /intelligence/recovery`, `GET /intelligence/progression/{id}`, `POST /intelligence/progression/{id}/decision`, `GET /intelligence/stalls`, `GET /intelligence/notices`, and `.../explanation` for targets and muscles (contract `intelligence.yaml`). `MuscleStateOut` gains `readiness_population` and `algo_version`.
- **Demo data:** `seed_demo` now adds 10 earlier weeks of push/pull/legs before the detailed fortnight (`--history-weeks 0` for the old behaviour).

### Changed (v6)
- Muscle states, the drill-down, quests and the weekly review read recovery-v2 instead of load-v1.
- The logger's target comes from the progression engine, and from last session only when there is no suggestion.

### Fixed (v6)
- prog-v1 no longer gives a bodyweight set above the top of its rep zone a lower target (22 push-ups in a 12-20 zone came back as 21); found by a property test.
- The logger's Last time panel no longer says progression is still to come; the suggestion card's e1RM is labelled as smoothed, matching the Why panel's last-session e1RM.
- "You vs population" only says your muscles recover slower or faster when the 90 % interval of your factor excludes the population value; otherwise it says "about like the population so far".
- Choosing a bodyweight move no longer paints the 40 kg default for one frame before the added load drops to 0 (a race a test caught under load).

### Documentation (v6)
- ADR-0014 (recovery-v2), ADR-0015 (prog-v1), ADR-0016 (explanations and the System's voice) and ADR-0017 (evaluation on synthetic users).
- `docs/ai`: the AI feature map, AI-off table and decisions list cover the new engines; adaptive planning describes prog-v1 and deload-v2; the evaluation lists its limitations in one place.
- README: a v6 intelligence-layer section with its honest limitations.

### Changed (v5 redesign)
- **New "System" colour palette and type scale** (UI-1). Navy-black surfaces, System blue
  for System UI and controls, arcane violet for XP and levels, gold for PRs, and rank colours
  E to S, in both themes. Every text colour meets WCAG AA (4.5:1) on every surface, and a test
  checks it straight from the stylesheet. Card and window headers use Rajdhani in the
  "window header" style; numbers are tabular. See `docs/development/design-system.md`.
- **One colour per muscle status** (UI-4). The map, its legend, the hover card and the "ready
  to train" pulse now use the same token for each status; a ready muscle pulses with a green
  outline (the "ready" colour) instead of System blue or a neutral ring.
- Only Latin and Latin Extended font files are bundled (font files 1,034 KB → 496 KB).
- **The System window** (UI-2). One reusable "System" notice window (glass, corner brackets,
  `[ BRACKETED ]` header, a 220 ms entrance and one scan line; a 120 ms fade with Reduce
  motion), used only for System events: the daily quest, **level up / rank up** and **quest
  complete** notices (new, top-right, on any page), **Skill acquired**, and a recommended
  **deload**. Modal windows trap focus and close on Esc; notices are announced to screen
  readers. Notice, quest and skill windows are tinted by rank (E-C blue, B-A violet, S crimson);
  data colours never change with rank (UI-7, tint part).
- **New app shell.** The rail reads Today, Train, Exercises, Skills, Progress, Fuel, Coach,
  History, Import & export and Settings (same order, so Ctrl+1…0 are unchanged; the shortcut
  shows on hover). The top bar shows the page title in the display face, then your **rank
  badge**, level, a **10-segment XP bar** that fills with a count-up (at most 600 ms, instant
  with Reduce motion), your **streak flame**, and an **AI status dot**: green when the local
  model is answering, amber when AI is on but the model is not running (rule-based tips),
  grey when off. Clicking the dot still switches AI on and off.
- **Today, redesigned ("Hunter HQ")** (UI-2). The page now leads with the **Daily Quest** in a
  System window (each task's progress, time left until local midnight, the reward and
  "Start today's session") and a **Status** panel (rank, level, XP and five stats), both above
  the fold at 1280×720. The morning check-in moved below them and still collapses to a
  one-line summary once done; then Insights (at most three, each with a "Why?"), Fuel rings
  and the muscle map. A recommended deload appears on Today as a System warning.
- **Five computed stats: STR, AGI, END, VIT, INT** (`stats-v1`, new `GET /game/stats`). Each
  is a 0-100 score from your own logs (skill-tree steps, best e1RM vs body weight, cardio
  minutes, check-ins, meals and quests), never allocated by hand, and each has a "Why?" that
  lists its formula and the numbers used. See `docs/architecture/hunter-stats.md`.
- **Train is a keyboard-first, three-pane logger** (UI-3). Left: this session's exercises and
  the library. Middle: the active exercise with **last session's sets in grey** next to
  today's, a target line ("Target: 60 kg × 8 @8, last time, Sat 18 Oct"), the input row and a
  thin rest bar that shrinks under the active set. Right: muscles hit, the full "last time"
  list, the skills the exercise feeds and the session's muscle load.
  - The inputs fill in from last time's matching set, so **Enter alone logs it** and the next
    set fills in; five sets of an exercise you have done before take five keystrokes. Works
    for reps, holds (seconds pre-filled) and timed sets (duration pre-filled).
  - Tab moves reps → load → RPE. A saved set flashes the accent for 150 ms. Space pauses or
    resumes the rest timer when you are not typing.
  - New `GET /exercises/{id}/previous` (the last finished session's sets of one exercise; the
    session you are logging is never its own "last time").
  - Targets repeat last session for now; suggestions that add load or reps belong to the
    progression engine, which is not part of this release.
- **Skill-tree canvas** (Skills page, the new default "Tree" view; "Cards" keeps the old
  grid). Every tree of a family is drawn as nodes and edges: mastered steps with a check,
  the current step with a % ring and a soft glow, locked steps dimmed with a lock, and each
  state also in words for screen readers. Wheel zooms, dragging pans, "Centre on current"
  and −/+ buttons; one family is fitted into the window (down to 50%), "All" fits the width
  and pans. Arrow keys move along the edges and between trees, Home jumps to the current
  step, Enter selects. A drawer shows the selected step's criteria with progress, the
  time-to-unlock estimate (only with enough data), feeders, "Train this skill", "Log" and a
  link to the full tree page.
- **Ctrl+K command bar** (also the "Log or ask…" button in the header). Type what you did
  or where you want to go: "bench 80x5 @8" logs a set (starting today's session if none is
  open; kg or lb, your units by default), "pull-up x8" a bodyweight set, "plank 45s" a hold,
  "weight 81.4" a weigh-in, "lunch chicken rice" a meal (meal from the word or the time of
  day), "train front lever" adds the skill to today's quest, "dark"/"light" switch the
  theme, "ai off" turns the local AI off, and a page name opens it. Anything else goes to
  the Coach as a question. The parser is rule-based: no model is involved. Exercise names
  are matched against the library (names, aliases and abbreviations such as "ohp", "rdl",
  "db"), with the top three matches offered. Arrow keys pick, Enter runs, Esc closes.
- Command bar: **ten quick actions** when the field is empty (actions that need details,
  such as "Log body weight…", put a template in the field instead of running), **N×M sets**
  ("log 3x8 pull-up", "log 5×5 back squat at 100 kg") and **"add N <food>"** portions
  ("add 2 eggs", meal from the time of day).
- **Awakening onboarding**: five skippable steps (name, units and body data; focus,
  calorie goal, activity and days per week; an equipment checklist; a baseline test; and
  "[SYSTEM] You have been selected" with rank, starting targets and the first daily quest).
  - The **baseline test** (max push-ups, pull-ups or dead hang, plank, squats in 60 s,
    optional weight; built-in stopwatch and 60 s countdown) is logged as one real
    max-effort session through the normal set logger, so it seeds XP, rank, skill trees and
    stats like any set. New `POST /profile/baseline`; the results are kept on the profile.
  - The **equipment checklist** is saved on the profile (also editable in Settings) and
    enforced in the daily quest's suggestion and in "Train this skill" items: a
    dumbbell-only user is never suggested a barbell exercise. An empty checklist filters
    nothing, so existing profiles behave as before.
  - Profile gains `focus`, `equipment` and a read-only `baseline` (migration 0013; old
    clients that omit the new fields keep working). See `docs/architecture/awakening.md`.
- **Streak details**: the flame in the top bar opens a short explainer with the current and
  best streak, freezes held (of 2) and used, and the rule that a missed day never removes
  XP, levels, ranks or unlocked skills. The Comeback item a missed day adds to the next
  quest is labelled "Recovery quest · no penalty".
- **Optional sound effects** (UI-7), off by default: short WebAudio tones (no audio files)
  for a logged set, a cleared quest, a level-up and a new skill, with a volume slider and a
  Test button in Settings → Appearance. Kept in this browser profile, so no API change.
- **States**: a compact inline error with Retry (used by the check-in card instead of raw
  error text) and an optional action button on empty states.
- README: the v5 interface (Today, Train, Skills, Ctrl+K, Awakening, streaks, accessibility)
  with new screenshots; page names follow the new labels (Dashboard → Today). Design-system
  and motion docs cover the new screens, components and effects. Programmatic focus targets
  (the page heading after navigation) no longer show a focus ring, and stepper fields hide
  the browser's spin arrows.
- Fix: Esc pressed right after Ctrl+K now closes the command bar (the field is focused at
  once, and Esc works wherever focus is inside the bar). Measured in headless Chromium: the
  bar opens in 78 ms the first time and about 30 ms after that.
- Fix: results that appear under a resting mouse pointer no longer steal the command bar's
  selection (only moving the pointer changes it), so Enter always runs the highlighted
  best match.

### Added
- **Calisthenics skill trees** (Skills page, Ctrl+4): 12 trees covering muscle-up, one-arm push-up, dips,
  plank to V-sit, headstand to handstand push-up, pistol squat, front lever, back lever, planche,
  human flag, nordic curl and dragon flag. Each step has unlock criteria such as "3×8 Pull-up" or
  "3×20 s Tuck L-sit".
  - Progress is computed from your logged sets (`skills-v1`): a step unlocks after two qualifying
    sessions within 42 days.
  - Each tree shows the current step and the % to the next, best values, feeder exercises and its
    sources. Steps with uncertain thresholds are marked as such.
  - A time to unlock is shown only once there is enough data (3+ sessions over a week with an
    upward trend), and it is labelled as an estimate.
  - "Train this skill" adds today's work for the tree to your quest, at most 4 items a day.
  - Unlocking a step gives XP and a **Skill acquired** moment. With Reduce motion on, it appears
    without the animation.
  - See `docs/architecture/skill-trees.md`.
- **Timed holds are first-class sets.** Planks, L-sits, levers and handstands are logged in seconds,
  with optional added load. The logger has presets and a stopwatch, the PR for a hold is the longest
  one, and imports from Strong/Hevy keep the seconds.
- **Exercise gallery** (Exercises page): 873 exercises from free-exercise-db (Unlicense), plus
  ASCEND's own calisthenics progressions.
  - Each exercise has a thumbnail and is mapped to the 19 muscle regions.
  - Search covers names and aliases; filters cover type, muscle, equipment, difficulty and
    "added by me".
  - The detail view shows instructions, muscles, the skill trees the exercise belongs to and a
    "Log it" button.
- **Add your own exercise.** ASCEND suggests every field and shows where each value came from:
  a similar library exercise, keyword rules, the local AI (qwen3:4b, if installed) or wger.de.
  - You review the suggestions and confirm. Any field you change is marked as yours.
  - Duplicates of library exercises are caught.
  - Custom exercises count in muscle load, quests and stats, and can be removed (their sets stay).
  - Every suggested field shows a **confidence** (High / Medium / Low). When the offline data is not
    enough (a core field is only a fallback guess), the review says so in plain words and asks
    "Look it up online?" with **Allow once**, **Always** (turns the setting on) or **No**.
  - **Online research** asks wger.de (exercise data, CC-BY-SA 4.0) for the fields and Wikipedia
    (CC BY-SA 4.0) for a short summary, sending only the exercise name. The result is a **research
    report**: each field it found, with its value, a link to its source and the offline guess it
    would replace. You can keep the offline guess per field, edit anything, and nothing is saved
    until you confirm. wger matches names exactly, so a few spellings are tried (as typed, Title
    Case, Sentence case, lower case, "push-up" hyphens); no connection, timeouts and rate limits
    leave the offline proposal in place.
  - Settings → **Online research** is **off by default** and turns on after a consent step. When it
    is off and you have not allowed a lookup once, ASCEND makes **no network requests** (a test
    proves it). While it is on, the header shows an "Online research on" indicator.
  - Every lookup is written to a **local lookup log** (time, name, sources asked, outcome), shown
    in Settings with a Clear button. New endpoints `GET`/`DELETE /exercises/online-log`;
    migration `0012`. See ADR-0013.
- The demo seed (`app.devtools.seed_demo`) now logs morning calisthenics, so the skill trees show
  progress partway through.

### Added (earlier in this cycle)
- **A livelier muscle map.** One body on a small 3D card: it tilts a few degrees towards
  the mouse, flips front/back, shades each muscle softly, glows fatigued muscles and
  lets recovered ones (trained this week, ready again) breathe. Hovering a muscle lifts
  it and shows sets, volume and when it was last trained; clicking opens the drill-down,
  which now slides open and closed.
- **Volume view** on the muscle map: colour by sets over the last 1, 7 or 30 days, with
  the colours blending as you switch. Backed by a new `GET /muscles/activity?days=`.
- **Level and XP in the header** on every page: logging a set or finishing a quest
  slides the bar forward with a "+N XP"; a level-up gets a short confetti burst.
- Dashboard XP bar animates from where you left it, numbers count up, rings draw in,
  the streak flame flickers, cards highlight on hover, a logged set slides into the
  table with a check, loading skeletons shimmer and pages fade in.
- **Settings → Reduce motion** (stored as `reduce_motion`). With it on, or with Windows
  animation effects off, nothing tilts, flips, counts or bursts; level-ups are still
  announced to screen readers. See `docs/development/motion.md`.
- First run: the setup card shows "Step 1 of 2 / Step 2 of 2" and counts up your starting
  targets, and a brand-new Dashboard opens with a welcome card (Log a set / Log a meal)
  until your first XP.
- Coach: replies are announced to screen readers, new messages slide in and stay in view,
  suggested questions fill and focus the box, and "ARC is thinking" shows typing dots.

### Changed
- Settings are grouped into **Appearance** (theme, reduce motion) and **Units & training**.
- Pages other than the Dashboard load on first open, so the main bundle is 16% smaller
  (407.8 kB to 341.7 kB; 142.1 kB to 125.4 kB gzipped).
- One date style everywhere ("Today · Tue 20 Oct", "Sun 18 Oct"); Diet targets carry their
  unit ("of 2,885 kcal", "of 109 g"); deload checks write "3% or more" and "50%".
- Diet gives the food table more room in small windows (1024 px), and its plate and meal
  buttons name the food or meal for screen readers.

### Fixed
- `seed_demo --wipe` now also removes exercises you added (they are user data); before, a re-seed
  kept them and a repeat "add" of the same name was refused as a duplicate.
- Switching pages now starts the new page at the top. Before, it kept the previous page's scroll
  position, because every page shares one scroll container.
- Add exercise: the research report shows readable values ("Lower chest", "Barbell") and marks each
  online value as agreeing with or differing from the offline guess. The "Keep offline" button's
  accessible name now contains its visible text (axe `label-content-name-mismatch`).
- **XP farming closed (`xp-v3`)**: deleting a set takes its XP back; editing can remove a PR's XP
  but never add it; set XP stops after 10 sets of one exercise or 40 in a day; PR XP is paid once per
  exercise per day (3 a day) and not for a jump of more than 25% (likely a typo); the session bonus
  needs 3 sets or 10 timed minutes, counts at most 10 minutes per set and is paid twice a day at
  most. Corrections appear in the XP history as their own rows. Full list:
  `docs/operations/loophole-sweep.md`.
- Sets logged after midnight count toward the new day's quest.
- Holds over an hour are refused (a minutes/seconds typo); sessions keep their order if the clock
  jumps back.
- Imports skip future-dated sessions and sessions already logged in ASCEND.
- Bodyweight exercises start at 0 kg added load instead of the barbell default of 40 kg.
- "Log it" from the gallery opens the logger on that exercise.
- Muscle map: the "Ready to train" key now matches the pulse on the figure.
- Deload card: "No key lift has dropped 3% or more in e1RM" replaces "…on: no key lift".
- The Dashboard no longer flashes its loading skeleton on reload.
- Quest suggestions come from ASCEND's core exercises, your own and those you have logged.

### Fixed (earlier in this cycle)
- A level-up counted the XP number down from the old level and slid the bar backwards;
  a new level now starts from zero.
- Deleting a meal that fails now shows an error instead of failing silently.
- The page heading no longer starts focused (and outlined) when the window first opens in
  development mode.
- Counts of one read "1 set" and "1 rep" (History, the training session header and the
  finish toast showed "1 sets").

## [0.3.0] - 2026-10-20

Release notes: [docs/releases/v0.3.0.md](docs/releases/v0.3.0.md).

### Import, export and backups
- New **Import & export** screen: pick or drop a Strong or Hevy CSV, preview what will be
  imported (sessions, sets, unmatched exercise names, dropped rows), then confirm.
  Re-importing the same file adds nothing. Imported history counts towards muscle load and
  PRs but gives no XP, and History marks imported sessions with their source.
- Backups (engine only, no screen yet): `POST /backup` writes an `.ascendbak` file
  (SQLite snapshot plus a manifest with a SHA-256 checksum), `GET /backups` lists them and
  `POST /restore` restores one after first saving a safety copy of the current data.
- Before an update migrates the database, the old database is backed up automatically;
  the newest 5 automatic copies are kept.

### Coach
- Every local-AI reply is checked before you see it. A reply with a number that is not in
  your data or your question (rounding within 2%, same unit), a medicine or dose, a diagnosis or a claim
  that your plan was changed is replaced by the rule-based tip, with a short note why.

### App
- Loading skeletons, empty states with a next step, and errors that say whether the
  engine is unreachable, on every screen. Stale data stays visible with a notice.
- Accessibility: AA contrast for text and status colours in both themes, a skip link,
  focus moves to the page heading, Ctrl+1…8 page shortcuts, Enter logs a set, Esc closes
  the muscle drill-down, error toasts are announced, every chart has a "Show the numbers"
  table, and reduced motion is respected.
- Back and Forward switch pages.
- The workout list can be filtered by section, source and date range.

### Project
- Engine events go through a transactional outbox with retries, and `GET /events` streams
  them as server-sent events (resumable with `Last-Event-ID`).
- Request bodies reject unknown fields with a 422 naming the field; profile updates still
  ignore read-only fields sent back by the app.
- Windows installer configuration: per-user NSIS install that keeps your data on
  uninstall, app icons, Electron fuses and a hardened sidecar build with a smoke test.
- Docker: hardened sidecar image and compose profiles for tests, development, the web
  renderer and MLflow, checked in CI.
- Database migrations 0008 (event outbox) and 0009 (workout source and import key).

### Fixed
- History showed runs and other timed sets as "1 reps".
- Some CSV files could not be read when picked from the file dialog.
- Found in the release click-through: long pages without buttons (History) could not be
  scrolled from the keyboard; the Edit/Delete links in the set table and the selected
  exercise's details were below AA contrast; chart dates could print on top of each other
  at the right edge; the weigh-in box suggested 75.0 kg whatever you weigh.

## [0.2.0] - 2026-10-20

### Training
- One logger for six sections: **Gym, Calisthenics, Cardio, Martial arts, Flexibility
  and Meditation**, with 23 seeded activities. Timed sets take a duration (minutes, m:ss
  or h:mm:ss), plus distance and average heart rate where they make sense.
- Edit or delete any logged set; PR flags and muscle load are recalculated.
- Calories for activities use MET × body weight × time (estimate). Session XP counts
  active minutes (`xp-v2`); muscle load counts timed work (`load-time-v1`).
- Morning check-in (sleep, energy, soreness, mood) gives a readiness score
  (`readiness-v1`). Amber trims one set from today's training quest, red swaps it for
  mobility, and the reply says honestly when training had already started.
- Deload advice from four recovery signals plus a planned deload after long training
  blocks (`deload-v1`), with a one-click deload week.
- Weekly review: sessions against plan and the top findings with suggestions
  (`review-v1`).

### Progress
- New **Progress** screen: weight trend (`trend-v1` smoothing) with weigh-ins, an ETA
  range to your goal weight (an estimate, not a promise), eight weeks of volume,
  sessions or minutes, personal records and tape measurements.
- Muscle drill-down: tap any muscle row for 1, 7 or 30 days of effective sets,
  readiness and the sets that loaded it.

### App
- Light theme and a "System" option that follows Windows.
- Metric or imperial units everywhere (kg/lb, cm/in, km/mi); data stays stored in SI.
- Settings: theme, units and training days per week.
- `/health` reports the database migration and turns "degraded" if it lags the code.

### Machine learning (developer-facing)
- Working classifier pipeline in `ml/`: prepare (dedupe, stratified split, team photos
  test-only), MobileNetV3-Small training with MLflow, ONNX export with a parity gate and
  SHA-256 manifest, evaluation (top-1/top-3, macro-F1, calibration). It runs end to end
  on a synthetic smoke set; no food model ships in this release.

### Project
- CI on Windows and Ubuntu for every branch, nightly runs, commit-message linting,
  a contract drift check between the sidecar and `docs/contracts`, and an ML workflow.
- Database migrations 0003 to 0007 (activities, body metrics, check-ins).

### Fixed
- The Bearer token scheme is now required on every request.
- Chart axes cover the largest value; empty 204 responses no longer show as aborted.

## [0.1.0] - 2026-10-20

First skeleton: Electron + React desktop shell, FastAPI sidecar with SQLite, workout
logging with PRs, Indian food log with approximate IFCT/INDB-style values, muscle
recovery map, XP, quests and streaks, rule-based coach with optional local AI.
