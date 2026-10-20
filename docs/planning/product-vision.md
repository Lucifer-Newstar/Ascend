# Product Vision

> How the finished ASCEND v1.x looks and behaves, from the user's seat. Scope and
> release split: [features.md](features.md). Mockups (rendered HTML/CSS at 1920×1080)
> live in the v2 plan; the HTML doubles as the starting point for React components.

---

## 1. One-line pitch

**Your training, scored like a game and explained like a coach — on your own PC, with
nothing sent anywhere.**

## 2. Who it is for

| Persona | Needs | ASCEND answer |
|---|---|---|
| **The student lifter** (primary) — trains 4–5 days a week, eats home food, low budget | Fast logging, progress he can see, Indian food that logs in seconds | One logger, PRs, muscle map, katori/ladle portions, photo scan |
| **The returning beginner** | A plan that adapts, no shame for missed days | Adaptive planner, humane penalties, streak freezes, AI-off simplicity |
| **The privacy-minded user** | Health data and body photos stay private | Local SQLite, optional encryption, no accounts, no telemetry |

## 3. The core loop

```text
Morning: open app → 20-second check-in → readiness → today's quest sized to it
Train:   log sets (Enter = done, Space = rest) → PR toast → XP → muscle map updates
Eat:     scan or search a meal → pick from top-3 → adjust katori/oil → rings fill
Night:   all three rings closed → completion animation → streak +1
Sunday:  weekly review — 3 findings, each a plan diff you Apply / Edit / Keep
```

## 4. Screens

| Screen | What the user sees |
|---|---|
| **Dashboard** | Three rings (daily tasks, kcal eaten, kcal burned — burn labelled *estimate*), today's quest with XP, the anatomical front/back muscle map with hover tooltip, a "needs attention" list, a coach proposal card, week strip, nutrition summary, recent PRs |
| **Coach (ARC)** | Chat with streaming replies; English, Tamil/Hindi beta with "Show in English"; a side panel with the data ARC used, active injury flags, AI on/off, rules-only, approval toggle, local engine status |
| **Workout logger** | Sets/reps/RPE table with previous and target, active-row editing, rest timer, PR flag, plate calculator, next exercise, this session's muscle map |
| **Diet / meal scan** | Photo with item boxes and confidence chips, top-3 per item, one question when unsure ("coconut or peanut?"), portion unit + oil level, totals vs target |
| **Progress** | Strength/stamina/flexibility/consistency KPIs, weight trend with 7-day average and projection cone, ETA as a range with confidence, measurements, blurred progress photos, PR records view |
| **Muscle drill-down** | One muscle selected, range slider 1 day → 1 month, daily bars vs target band, recovery curve, every contributing set with its mapping weight, one suggested fix |
| **Quests & Rank** | Daily quest, weekly challenge, rank and trial requirements, streak + freezes, stats radar |
| **Activity Gallery** | ~800 exercises (free-exercise-db, public domain) + Indian additions, with demo, muscles, cues, mistakes |
| **History** | One timeline of workouts, meals, metrics and quests, filters, calendar heatmap, full-text search |
| **Settings** | Profile, units, language, AI tier/off, notifications + quiet hours, backup/export, diagnostics, About (licences) |

Sidebar groups: **Home** (Dashboard, Coach, Quests & Rank) · **Train** (Gym,
Calisthenics, Cardio, Martial arts, Flexibility, Meditation) · **Track** (Diet,
Progress, PRs, History, Activity gallery) · bottom: Settings + local AI status.

## 5. Look and feel

- **Windows 11 native frame:** 32 px title bar with Ctrl+K search, real min/max/close and
  snap layouts (`titleBarOverlay`), 232 px sidebar, 12-column content grid.
- **Dark first** — bg `#090C12`, surface `#111723`, accent cyan `#22D3EE`, XP violet
  `#8B7CFF`. Glow only on the primary button, active rings and the selected muscle.
- **Type:** Inter (tabular numbers), Rajdhani only for level/rank, JetBrains Mono for logs.
- **Motion:** 150 ms hover/press, 250 ms panels, 900 ms ring completion; all off when
  Windows "reduce animations" is on.
- **Every data view ships empty, loading and error states** (error says what failed,
  confirms data is safe, offers Retry + a fallback + "Open logs").
- **Accessible:** keyboard-first, hatching (not colour alone) on the muscle map,
  screen-reader labels per muscle region. Light theme after v1.0.

## 6. What it will never do

- Send data off the PC, show ads, or require an account.
- Let a language model change a number, a plan or a target without the user's OK.
- Take XP or levels away as punishment.
- Give exercise advice after red-flag symptoms — it says "see a doctor or physio" instead.
