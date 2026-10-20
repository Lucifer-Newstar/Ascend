# Changelog

All notable changes to ASCEND. Versions follow [Semantic Versioning](https://semver.org/);
entries are grouped from Conventional Commits and written for users first.
Formula and model versions are listed where a number you see could change.

## [Unreleased]

### Added
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
