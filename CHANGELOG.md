# Changelog

All notable changes to ASCEND. Versions follow [Semantic Versioning](https://semver.org/);
entries are grouped from Conventional Commits and written for users first.
Formula and model versions are listed where a number you see could change.

## [Unreleased]

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
