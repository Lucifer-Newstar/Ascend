# Changelog

All notable changes to ASCEND are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Entries are grouped from
Conventional Commits and written for users first. Formula and model versions are listed
where a number you see could change. User-facing release notes live in
[docs/releases](docs/releases/).

## [Unreleased]

### Added

- **Your training week** (Settings > Trainer): pick the days and a usual time. The other days
  are planned rest, and the weekly target follows your days. The Planner shows this week
  planned vs done, and on Sunday you can plan next week.
- **10-minute version** of today's session on Today and the lock screen: the first moves at two
  sets each. It counts for your streak like any session.
- **The lock screen is the workout door**: "Today: Push A · 4 moves" with Enter to start, or
  "Rest day ✓". It can be switched off.
- **The trainer builds your plan from chat.** Say "I have an 8kg dumbbell and two 5kg", "I have
  a punching bag", "I want to train muay thai", "I trained kicks 3 years ago" or "I can't eat
  much but I can drink" and the trainer offers to update your plan: strength days sized to your
  dumbbells, Tuesday and Saturday skill days that start gently after a break, two rest days,
  protein and shake targets (no oats). A too-fast weight goal gets plain words and realistic
  targets. **Build my plan** on the Chat page is an optional six-question version. Every
  change is a card with undo; works with the AI off.
- **Tray and start with Windows**, both off by default. With the tray on, closing the window
  keeps ASCEND by the clock and reminders still arrive.

### Changed

- Today's workout reminder waits for your usual training time (from an hour before) and names
  it; the evening check waits until an hour after it.

## [1.3.0] - 2026-10-25

v1.3 is the "kinder and more useful" release: the trainer can change your plan, settings, kit
and profile from chat (always as a card you confirm, with undo), streaks count training and
respect rest days, reminders are calm, and Today shows goals within reach instead of stats.
Database `0031` → `0032`; the app backs up your data before it migrates it. Release notes:
[docs/releases/v1.3.0.md](docs/releases/v1.3.0.md).

### Added

- **Trainer actions from chat**: "change my goal to bulk", "add a pull-up bar", "switch to the
  light theme", "rest 90 s on squats", "train 4 days a week", "switch me to upper lower". Each one
  is a card you confirm, cancel or undo, also by typing "yes", "no" or "undo". Works with the AI
  off. Specialties (Tara, Idris and the others) are labels only; one trainer answers.
- **Chat page** with the big trainer portrait, sharing one conversation with the chat drawer;
  **Ctrl+K** focuses it.
- **Log lines in plain words**: "3x10 push-ups", "plank 45 s", "weighed 71.2", "2 idli and
  sambar" become one card. Foods resolve by alias, base dish and typo; unknown foods open
  **Add your own food** with the name filled in. Fuel searches the whole food table.
- **Near goals on Today** ("Within reach"): lifetime sessions with the next milestone (1, 3, 5,
  10, 25, 50, 100), E1-E3 style sub-ranks, best streak and weeks in a row at your weekly target.
- **Welcome back**: +25 XP for the first session after a missed day, once a week, and a kind line
  from the trainer.
- **Exercises and kit**: burpee, jumping jack and wall sit; bench as a kit choice; rings count as
  a bar; held slots show seconds in the planner.
- **Two new trainers**, Tara and Idris, and redrawn portraits for Vera, Kai and Dario.
- **docs/RULES_AND_BASELINE.md**: the design and technical rules, the measured baselines and the
  automated checks (`make rules`, `scripts/check_rules.py`, `tests/rules/`).

### Changed

- **Streaks count training only** (a finished workout or a logged set); a planned rest day of
  your program is neutral; a missed day with a reason still counts as rest.
- **Reminders are calm**: at most two a day, none on a planned rest day, no water reminder and no
  "your streak ends at midnight". The evening check, the monthly photo reminder and the weigh-in
  nudge are new switches in Settings, all **off** by default.
- **Streak unlocks became session unlocks**: Crimson Gate and Ronin at 10 sessions, Focus Charm at
  25, Spear of Valor at 50. Anything you already earned stays.
- **Today** puts the weekly boss right under the trainer; the five hunter stats moved to Profile.
- **Progress** leads with training: this week, sessions all time, lifts, bands and PRs come before
  body weight; a recovering muscle shows when it is ready instead of "0%".
- The planner doses push-ups, pull-ups and holds from your baseline test and no longer blocks an
  underweight user who wants to gain.

### Removed

- **AI photo feedback** (and its vision model in AI setup, the `photo_feedback` setting and
  `/photos/feedback*`). Photos, side-by-side compare and backups are unchanged; asked to rate a
  physique, the trainer says it does not rate bodies.

### Fixed

- "Switch me to upper lower" is a program change, not an exercise swap; locked themes stay locked
  when asked from chat; a profile value that is already set says so instead of proposing nothing.
- Built-in programs swap moves your kit cannot do; an empty food search lists every food with
  everyday names first; long questions need more than one keyword before a help note answers.

### Versions

Chat edits parse with `actions-parse-v2`; the trainer's watcher (`watch-v1`) gains the
welcome-back rule and the opt-in photo and weigh-in rules; the `themes-v1` unlock rule for
Crimson Gate changed. The XP formula (`xp-v1`) is unchanged; sub-ranks are display only.

## [1.2.0] - 2026-10-23

v1.2 is the "make it feel like a game, and make it simpler" release: a real start screen, app
themes, a big trainer with moods, avatars and cosmetics, seasonal bosses, programs in every
section, a weekly recap video and India's food guide. Built on the `v12-test` branch and tested
on a real PC before it goes to `main`. Database `0025` → `0031`; the app backs up your data
before it migrates it. Release notes: [docs/releases/v1.2.0.md](docs/releases/v1.2.0.md).

### Added

- **App themes** (`themes-v1`): Shadow (the new default), Crimson Gate, Frost, Emerald and Solar
  Gold, each with its own landing art, frames, buttons, timer and event screens, plus the old
  Light and Dark looks. The four extra themes unlock with a 7-day streak, rank D, your first
  weekly boss and rank C. Text always sits on a solid panel; every theme passes an automated
  WCAG AA contrast test. **Settings > Appearance > Background art: On / Dim / Off.**
- **System intro and a three-step onboarding**: Begin or Restore my data, then your body (empty
  fields, no placeholder numbers), your goal in plain words and your kit. Your weight is saved as
  your first weigh-in.
- **Lock screen on every launch**: the landing art with your hunter tile (avatar, name, level and
  rank) and the time, like a desktop sign-in. Click it or press Enter to zoom into Today. No
  password (ASCEND has none).
- **Big trainer with moods** (neutral, hyped, proud, warning) on Today and in the chat, with new
  Iskra and Vera art. **Trainer reminders**: today's workout, a missed day's reason, a streak at
  risk, water and the check-in, as a desktop notification and a bubble on Today (Settings >
  Trainer > Reminders).
- **Exercise animations**: every library move and drill plays a smooth 2-frame loop with three
  short form tips in Train, Exercises and the full-screen timer, and 25 of the most used
  moves play a proper looping animation.
- **Solo-safe martial arts**: 16 drills for boxing, kickboxing and Muay Thai solo work, basic
  kicks and stances and fighter conditioning, all done alone (no partner, weapons, grappling,
  throws or locks).
- **Loadout and class**: the kit you pick (for example rings and bodyweight, "Calisthenics
  Ronin") filters Train, Exercises, Skills, the Planner, programs and quests; "Explore all" shows
  the rest greyed out with what gear they need.
- **Programs v2**: 12 more built-in programs, so every section has Beginner, Intermediate and
  Expert, plus Mobility and Calm starters. In every section: pick one, **Generate one for me**
  (offline rules) or **Build your own**. **Follow your program**: Today's quest and the trainer
  follow it, and every exercise in it can be logged.
- **Bosses** (`boss-v2`): tiers E to S by level and category (strength, calisthenics, cardio,
  martial arts), a boss ladder on Profile, a full-size boss screen, and four seasonal bosses
  (Harvest Colossus, Winter Wraith, Monsoon Serpent, Shadow Sovereign) that drop their own
  cosmetic.
- **Avatars and cosmetics**: a male or female avatar that ranks up E to S (rank, gear and aura,
  never body changes) and a catalog of 17 outfits, weapons, relics and pets earned by streaks, PRs, bosses
  and seasons. Faith-flavoured items are optional, behind a "themed items" switch, with neutral
  names.
- **Full-screen timer**: a run-through view with a big countdown, the move's animation, sets,
  what is next and a trainer cue; the screen stays awake until the timer ends.
- **Workout finish moment**: XP, rank progress and a trainer reaction, with the 3-set rule
  explained.
- **Weekly recap** (`recap-v1`): a short video of your week on Progress (sessions, records, the
  boss, your streak and habits, rank), drawn on your PC and saved as a WebM file. No body numbers.
- **India's food guide** (`foodrules-v1`): the ICMR-NIN 2024 Dietary Guidelines for Indians in
  plain words on Fuel, with a check of today's plate by food group and up to three kind tips. It
  never changes your targets.
- **Bigger food list**: 157 everyday Indian foods (milk, bread, oats, paneer dishes, Maggi and
  more) and **Add your own food**.
- **Tester save** for checking the release: a normal backup with everything unlocked.

### Changed

- **Streak rule**: miss a day and give the reason by the next day, and the streak is kept; two
  missed days in a row, or no reason, resets it. This replaces the automatic freezes.
- **Today** shows only today's quest, today's workout, your streak and the boss.
- **Settings** has six sections; Import & export moved into Settings > Data, and "Today's
  numbers" and "Online research" into Settings > Advanced.
- **One chat box**: the Ctrl+K command bar is part of the trainer chat, and it answers "what
  should I train today?", "I missed a day" and "log 3 pushups" without a local AI. The local AI
  is off unless a model is installed.
- **Plain words**: simple muscle names; effort, estimated max and energy terms sit behind
  "details"; no version labels in the app.
- The meal planner moved from Planner to Fuel; "Sessions by source" on History shows only after
  an import.
- **Photo safety**: progress photos blur again when you leave the app, a backup can leave the
  photos out (Settings > Data > Include progress photos), and Settings > Privacy has **Delete all
  progress photos** and a plain list of where photos live. Photos never leave your PC.

### Fixed

- Custom and bodyweight programs: every item opens its own logger, and beginner targets fit your
  baseline.
- No false "above range" muscle warnings after a few push-ups, no fake "Mastered" steps, no 75 kg
  placeholder, and a realistic weight-gain estimate.
- Moves wrongly listed as bodyweight have the right gear; the Full Body programs no longer list a
  plank that could not be logged.
- The erase box and full-screen moments draw above every card; the morning check-in shows only in
  the morning; no console error when no plan is chosen.
- Every dialog (Share, boss screen, workout finish, erase, welcome, recap, timer) scrolls and
  closes on a 768 px screen and at 125% Windows scaling; a click on the backdrop closes it.
- Opening the app no longer fails a request when two screens spawn the weekly boss at once, and
  Today loads faster (a program day reads muscle recovery once, not once per exercise).
- Train and Today fit a 1024 px wide window; the trainer says the day is done only when today's
  quest is done; onboarding asks for your kit instead of saving none.
- "What should I train today?" with no program suggests a starting program for your kit instead
  of the day's protein tip; the program list scrolls so the exercise library stays on screen;
  body-weight sets show "BW", not 0 kg; a goal estimate in another year shows its years; a
  program's "next day" reason uses plain words and a short date; the session log scrolls
  sideways on narrow windows; a repeated toast replaces the last one instead of stacking.
- The Skills page draws all its trees at once instead of sitting blank while it asks for each tree
  one by one; XP numbers have digit grouping on both sides of the level bar ("12,541 / 25,974").
- Workout targets: after a big dumbbell jump the next target comes from your last sets, so it no
  longer asks for 3 × 1; targets on Train and Today use your program's rep range, and the
  logger's suggestion uses the program's number of sets, not last session's.
- "Lose fat" never sets a calorie deficit when you are under 18 or below a BMI of 18.5; the
  daily target stays at maintenance and the meal plan says why.

### Removed

- The AI status pill in the top bar and the Ollama step in the tour, the "Keyboard" card on
  Train, the muscle layers and Recovery/Volume switch on Today, muscle weights like "x0.375",
  the duplicate trainer switch and the Cut/Maintain/Bulk picker (your focus decides it).
- "BJJ Rolling" from the library.

## [1.1.0] - 2026-10-23

One trainer, one chat: the trainer you pick watches your log, answers questions, shows you
around and can propose changes that run only when you confirm them. New Planner and Profile
pages, five more skill trees plus your own, private progress photos and share cards. Release
notes: [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md).

### Added

- **Trainer and chat** from the top bar: help notes (`trainer-kb-v1`), rule-based intent
  routing before any AI call (`trainer-intents-v1`), goal checks and a watcher feed
  (`watch-v1`). Four trainers to pick from (onboarding or Settings), each with portraits per
  mood; weekly bosses have their own art.
- **Content selector** (`player-state-v1`, `content-catalog-v1`, `select-v1`): what the
  trainer says on its own is chosen from your level, readiness, consistency, diet adherence and
  weigh-in trend, with cooldowns and a cap of 3 posts a day; "why?" in the chat repeats the
  reason. Hard items are never picked on a low-readiness day, eat-less items never under 18.
- **Personalization** (`personalize-v1`, `quest-v3`): the daily quest's set range follows your
  experience level and readiness, and the nutrition item targets your own gap (meal logging or
  protein). Without a profile the quest is unchanged.
- **In-app actions** (`actions-v1`): logging sets, holds, weigh-ins and food, switching program
  and erasing data can be proposed by the chat, the command bar or the local AI, and run only
  after Confirm on a card (erase also needs the word typed), with an audit log and Undo.
  `packages/shared/src/command-vectors.json` is the one allowlist; tests on both sides read it.
- **Planner page**: build a week of training for your days, time and equipment
  (`plangen-v1`), a day of Indian meals for your diet (`dietgen-v1`), and check a goal against
  safe published rates (`goalcheck-v2`, ICMR-NIN 2024). Save, follow or delete what you build.
  Under 18 the planner never plans a deficit; **Hide calories** hides kcal numbers.
- **Profile page**: Hunter card (level, rank, streak, stats, titles), achievements to share,
  and the progress photo gallery.
- **Progress photos** (AI feedback `photo-feedback-v1`): stored only in your data folder, re-encoded and stripped of
  EXIF/GPS, blurred until you choose "Show photos", compared side by side, included in backups
  with checksums. Optional AI feedback on a local vision model: off by default, never under 18,
  and it never comments on body fat or weight.
- **Share cards** (`share-v1`): drawn on your PC with no weight, photos or profile details. Save
  the image, copy it, open X's own post composer (an allowlisted link; you post it) or save and
  copy the caption for Instagram.
- **Skill trees**: five new foundation trees (hanging leg raise, weighted pull-up, one-arm hang,
  split squat, plyo push-up), 17 built in. **Custom skills**: make a tree of up to 8 steps from
  library exercises; it unlocks from logged sets and pays no XP.
- **Guided tours**: one first-run flow (onboarding, trainer pick, then a five-step app tour)
  and a tour of any page on request.
- **AI setup** in Settings (`ai-tiers-v1`): Ollama and model detection, RAM/VRAM, a model
  recommendation, picker and test. The app works fully without a model.

### Changed

- **The Coach page is retired.** Its weekly review and deload cards moved to Progress, and
  questions go to the trainer chat (Ctrl+K sends any unrecognised line there). Planner takes
  its Ctrl+7 slot.
- Version 1.1.0 everywhere (packages, lockfiles, sidecar, bug-report template).
- Database migrations 0020–0025 (planner, trainer messages, selector picks, action log, custom
  skills, progress photos) run on first start; a backup is taken before they do.
- The planning documents are marked as design records; the outbox and `/events` stream are
  marked as unused in 1.1.

### Fixed

- **Clean install.** Development runs and demo data use `%APPDATA%\ASCEND-dev`, so they can no
  longer pre-fill the installed app; the demo seeder refuses the installed app's folder and is
  no longer packaged into the sidecar (a CI check fails the build if it is). **Settings > Start
  fresh** (and "start fresh" in the chat) erases your data after a backup and keeps the
  exercise library and food table.
- **Coach answers.** "Hello", "what can you do" or "erase my data" no longer get the day's
  muscle tip. Each AI fallback has its own reason and label (switched off, not running, timed
  out, model error, failed the safety check); a cold model gets 60 s on its first answer.
- **Windows CI.** The Dashboard and AddExercise page tests no longer time out on Windows runners.

### Security

- Three new Electron IPC channels, each validated in main: `image:save` (PNG/JPEG only, magic
  bytes checked, 16 MB cap), `clipboard:write`, and `share:open`, which opens only
  `https://x.com/intent/tweet` (or `twitter.com`, `/intent/post`) with a single `text` query.
- Still open: the installer is unsigned and backups (now including photos) are unencrypted.

## [1.0.0] - 2026-10-23

The first stable release. No new features (the feature freeze after v8 holds): 1.0.0 is the
0.4.0 app with the version made final, every document checked against the code, and a
release pipeline that publishes notes and checksums. Release notes:
[docs/releases/v1.0.0.md](docs/releases/v1.0.0.md).

**What ASCEND 1.0.0 is:** an offline Windows desktop fitness RPG. A keyboard-first workout
logger with progression targets (`prog-v1`) and four built-in programs (`programs-v1`); a
54-muscle recovery map (`recovery-v2`, `muscles-v2`); an Indian food log with an adaptive
calorie target (`tdee-v1`) and weekly insights (`insights-v1`); XP, ranks E to S, daily
quests, streak freezes, calisthenics skill trees and a weekly boss raid (`boss-v1`) with
Instructor Iskra Vey; daily automatic backups, restore, JSON/CSV export and Strong/Hevy
import; an optional local AI coach (Ollama, `qwen3:4b`) that only rephrases the engines'
numbers. Everything runs and is stored on the user's PC.

### Added
- GitHub Releases now carry `SHA256SUMS.txt` next to the installer, and the release text
  comes from `docs/releases/<tag>.md`; a release drafted by hand is updated instead of
  failing the publish job.
- CI job "docs": every relative link in the repo's Markdown files must resolve
  (`scripts/check_md_links.py`).
- Release notes for 1.0.0 in `docs/releases/v1.0.0.md`.

### Changed
- Version 1.0.0 everywhere (packages, lockfiles, sidecar, bug-report template). The
  installer is `ASCEND-Setup-1.0.0.exe`, and Settings → About, `/health`, exports and
  backups report 1.0.0.
- Documentation checked against the code: the README (download and install from Releases,
  the SmartScreen step, features, limitations, verified counts), the docs index, tech stack,
  local setup, contributing, release process, SECURITY.md and the folder READMEs.
- Package metadata (repository, homepage, bugs) points at the GitHub repository.

### Security
- Contains every fix from the October 2026 external review (3 high, 6 medium, 22 low
  findings; first shipped in 0.4.0, see below and [SECURITY.md](SECURITY.md)). Still open:
  the installer is unsigned, and backups are stored unencrypted (L14).

## [0.4.0] - 2026-10-23

Tagged on `main` after the security-review fixes. The version files still said 0.3.0 when
the tag was pushed, so this release's installer is named `ASCEND-Setup-0.3.0.exe`; the app
inside is the 0.4.0 code. It was the first release whose installer was built and published
by the release workflow.

### Security (October 2026 external review)
- **Electron 45.0.0** replaces the unsupported Electron 33 (H1).
- **Release build fixed and hardened:** `build/fuses.cjs` and the icons are committed, all
  nine Electron 45 fuses are set at pack time through `@electron/fuses` 2, and release.yml
  fails when a fuse is not set (H2).
- **The sidecar ignores inherited `ASCEND_*` settings**, `NODE_OPTIONS` and
  `ELECTRON_RUN_AS_NODE`; the packaged sidecar takes its token from stdin and binds
  127.0.0.1 (H3).
- Backups: a bad backup file no longer breaks the list or the daily backup (M1); restore
  accepts only files from the backups folder, with a size cap, an integrity check and no
  triggers or views (M2).
- Production CSP `connect-src 'self'` (M3); `OLLAMA_HOST` normalised and loopback only
  unless `ASCEND_OLLAMA_ALLOW_REMOTE=1` (M4).
- Complete, re-importable exports with local-date file names (M5) and CSV formula-injection
  protection (L15).
- Release job alone gets `contents: write`, every action pinned to a commit SHA, torch
  2.14.1 with `weights_only=True` loads (M6).
- XP integrity on edits, deletes and lost PRs (L8); sidecar restart limit, a 30 s IPC
  timeout, `export:save` validation and an HMAC proof on `/health` before the token is sent
  (L9-L12); the low findings L1-L7, L13, L16-L20 and L22 (see SECURITY.md).

### Changed
- Dependencies: React group, ESLint and type packages, build tools, electron-builder
  26.15.3, `@types/node` 26, `@testing-library/jest-dom` 7, jsdom 30, cross-env 10,
  concurrently 10, `@electron/fuses` 2; for ML: pytest 9.1, pillow 13, sqlalchemy 2.1.5,
  alembic 1.20, onnxruntime 1.31, pyyaml 6.0.3; GitHub Actions updates.
- The desktop toolchain needs **Node.js 22.22.2 or newer** (jsdom 30).
- Dependabot version-update pull requests are switched off (`.github/dependabot.yml`
  removed); GitHub's security alerts still apply.

### Fixed
- The XpChip count-up test no longer depends on effect timing (it failed now and then in CI).
- The level-up announcement is deterministic.

The v5 redesign, the v6 intelligence layer, the v7 diet engines and layouts and the v8
features were all built after 0.3.0 and shipped in 0.4.0:

### Changed (v8 game feel)
- **Moments:** level-up, rank-up and quest-clear notices now pop in with the trainer (or the rank badge in plain mode), a confetti burst and the new level; rank-up has its own title. A boss defeated while you watch plays its own moment on the raid card. All of it is transform/opacity only, and Reduce motion shows them still, without confetti.
- **Hunter profile** (was Status): your name, rank, level, XP, streak and your newest boss title.
- **Boss crest** on the raid card, which turns into a check mark once the boss is beaten.
- **Muscle map v2 artwork:** a full redraw with 7.5-head athletic proportions, tapered limbs, organic muscle bellies and one even seam width; the deep layer now sits over the whole ghosted body. Same 54 keys, views and layers, so nothing else changed; the file is 44.5 KB (was 99 KB). Generator and notes: `scripts/body_map/`.
- **Muted map colours:** the muscle map has its own muted status colours (`--color-map-*`: recovered teal-green, recovering amber, over dusty red, under slate blue), a toned-down volume ramp, and fatigued muscles get a thin outline instead of a glow. The Deep layer's ghost body is lighter, so the surface muscles stay visible behind the deep ones.
- The trainer's neighbouring lines no longer repeat a closer.

### Added (v8 boss raid)
- **Weekly boss raid** (`boss-v1`, ADR-0022). Each Monday a boss appears on Today with HP sized to a week of your training: your program's working sets (halved in a deload week), else your median sets per week over the last 4 weeks, else 20. Every training set you log that week deals 1 damage. Beat it by Sunday for **+150 XP** and the boss's **title** on your Hunter profile; if it survives, nothing is lost. The reward is shown before you earn it, and "Why?" explains the HP.
- `GET /game/boss`, `GET /game/titles`; migration 0019 adds `boss_raids`.
- **Dropped for v8:** achievements, login/check-in rewards and reminder notifications. The boss title is the only title source. The reasons are in `docs/research/v8-gamified-engagement.md` §4.
- The "haven't logged today" banner can be hidden for the day.

### Added (v8 trainer)
- **Instructor Iskra Vey**, an original anime-style drill instructor, speaks your insights on Today ("Iskra's briefing") and appears beside coach replies. Four expressions: calm, proud, stern (warnings) and fired up; the portrait crossfades between them (instant with Reduce motion).
- **The numbers do not change.** Each line is a fixed opener around the engine's own sentence, chosen deterministically from the insight's kind; a tip worded by the local model has already passed the coach's number guard. At most 40 words, second person, "Hunter". **Why?** is still one tap away.
- **Trainer switch** in the top bar and in Settings → Appearance, saved with your settings (`trainer`, default on). Off shows the same facts in the plain System style.
- Art provenance, prompts and licence status: `apps/desktop/src/assets/trainer/ART_PROVENANCE.md`; persona research: `docs/research/v8-trainer-persona.md`.

### Changed (v8 detailed muscle map)
- **54 muscles and heads instead of 19 regions** (taxonomy `muscles-v2`, ADR-0021, research in `docs/research/v8-anatomy.md`): the pectoralis major heads, pectoralis minor and serratus; lats, teres major, three trapezius parts, rhomboids, the rotator cuff, erectors and quadratus lumborum; the neck; three deltoids; biceps and triceps heads, brachialis, brachioradialis and the forearm groups; the abdominal layers; the glutes, TFL and hip flexors; the four quadriceps, sartorius, adductors, gracilis and the three hamstrings; calves, tibialis anterior and fibularis.
- **New muscle map artwork**, drawn for ASCEND: front, back and a **Deep** layer (pectoralis minor, rotator cuff, rhomboids, transversus, iliopsoas, vastus intermedius...) that ghosts the surface muscles. "All muscles" is grouped by region and every muscle opens its drill-down. Exercise tiles without a photo now show the body with the exercise's muscles highlighted. react-muscle-highlighter is no longer a dependency.
- **Every exercise re-mapped** by `muscle-map-v1`: free-exercise-db's muscle lists plus name rules (incline, decline, fly, dip, overhead, pushdown, hammer, preacher, seated calf...) from the research table in `docs/research/v8-exercise-muscle-mapping.md`. Custom exercises are split into heads the same way, from the rules, local AI or wger guess.
- 17 small or deep muscles show recovery only and never raise an "under-trained" or volume warning, because there is no evidence for weekly set targets for them. They are never quest targets.
- **Migration 0018** keeps a copy of the old rows, re-maps the library, translates hand-made weights, renames quest metrics and recomputes muscle load from your logged sets. No workout, set, meal, XP or quest is removed; a backup is written first and the downgrade restores the old rows. A test checks that a v7 history survives.
- One set now counts on several heads, so weekly sets per muscle are not comparable with v7's 19 regions. The recovery evaluation was rerun: recovery-v2 Pearson r 0.842-0.926 on the 54 muscles (v7: 0.848-0.946), still far ahead of a fixed 48 h rule (0.552-0.579). See `docs/ai/evaluation.md`.
- Custom exercises can list up to 40 muscles with at most 4 primary (was 8 and 3), since library exercises now carry more heads.
- `MuscleState` gains `region`, `parent`, `deep` and `readiness_only`; `map_slug` is the muscle key.

### Added (v8 hardening)
- **Daily automatic backups.** While the app runs, the sidecar saves one `.ascendbak` snapshot per calendar day (checked at start-up and about hourly) and keeps the newest 14. They sit beside the existing pre-update and pre-restore safety copies, which keep their own rotation; manual backups are never deleted.
- **Quick log on Today:** log one set, one meal or a weigh-in without leaving Today. A set goes into today's open workout (or starts one). Any quick log now keeps the streak alive: an active day is a finished workout, a completed quest item, or any logged set, meal or weigh-in.
- **"You haven't logged anything today."** A one-line banner on Today, shown only on days with nothing logged yet, jumps to Quick log.
- **"rough · based on N" badges** mark numbers that rest on too little data: the energy estimate before tdee-v1 turns adaptive (based on N days; settles after about 14) and a muscle's recovery factor while it still uses the population value (based on N sessions; about 8). The thresholds are design choices, listed in Settings → Today's numbers.
- **Settings → Today's numbers:** an audit table of every number on Today (level and rank, XP, streak, each quest item, the three rings, the five stats, the muscle map, energy burned) with the engine and version that computed it, how, and the data behind it.
- **Settings → Backups** lists every snapshot with its kind and size, has "Back up now", and restores one after a confirmation. The current data is backed up first, the database is reopened, and the window reloads.

### Changed (v8 exercise pictures)
- **No more empty picture boxes.** Every exercise card shows a photo or a designed tile.
  - Photos are re-fetched from free-exercise-db (public domain) at 320 px wide instead of 224 px: 873 webp files, 5,307,910 bytes in total (was 2,774,240).
  - 14 of ASCEND's own entries (e.g. Pistol Squat, Negative Pull-up, Nordic Curl Negative) now show the photo of the same or a similar movement; the detail view says "a similar movement". Migration 0017 sets them and leaves any picture you changed alone.
  - The other 56 (levers, planche, flags, martial arts, meditation, the 3 source entries without a photo) and every custom exercise get a tile coloured by section with a line icon and the main muscles. A photo that fails to load also falls back to the tile.
  - Tests check that every picture path exists, is a 320 px webp, and that the bundle stays under 25 MB.

### Fixed
- Opening the app on a new day could fail one request with a server error: two first requests both built today's quest, and the second hit the unique index. The second request now reads the quest the first one wrote.

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

[Unreleased]: https://github.com/Lucifer-Newstar/Ascend-/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v0.4.0...v1.0.0
[0.4.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Lucifer-Newstar/Ascend-/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Lucifer-Newstar/Ascend-/tree/v0.2.0
