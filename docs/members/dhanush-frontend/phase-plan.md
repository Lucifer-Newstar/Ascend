# Dhanush · Frontend Phase Plan

> **Purpose:** my delivery, handoffs and commit-sized tasks by phase. Shared scope: [features](../../planning/features.md). Gates: [phases](../../planning/phases.md). Dates (estimates): [timeline](../../planning/timeline.md). Tick a box when the commit is merged.

| Phase | I deliver | I need | Handoff / completion check |
|---|---|---|---|
| **0 · Foundations** | Secure shell, bridge, supervisor to target behaviour, design tokens, app layout | Sidecar `/health` (exists), CI from Gokul | Packaged app starts the sidecar; killing it shows `restarting` then `ready` |
| **1 · Core loop** | Logger, rings, muscle map + tooltip, history, onboarding, quest card | Workouts/progress/game APIs or mocks | Gate demo: log a set → map and XP change on screen |
| **2 · Local AI** | Chat UI with streaming, scan review chips, proposal diffs, job progress, AI status | Chat SSE + scan job API | Scan a plate and correct one item entirely in the UI; AI-off still usable |
| **3 · Ship v1.0** | States pass, settings, backup/restore UI, diagnostics, notifications, update UI | Backup/export/update APIs | Every screen passes the states checklist; Playwright smoke green |
| **4 · Breadth** | Martial arts, flexibility, meditation, gallery, photos compare, check-in, light theme | Section engines | All 11 sections usable; visual baselines approved |
| **5 · MLOps loop** | Model health page, corrections export UI | Prediction logs API | Export a corrections zip from the UI |

## Commit-sized tasks

### Phase 0 · Foundations (26 Oct – 8 Nov)

- [ ] `feat(desktop): harden BrowserWindow (sandbox, contextIsolation, CSP, deny navigation)`
- [ ] `feat(desktop): titleBarOverlay with Windows 11 caption buttons`
- [ ] `feat(desktop): single-instance lock focuses existing window`
- [ ] `feat(desktop): periodic /health check every 5 s with 3-miss restart`
- [ ] `feat(desktop): backoff 1–16 s and 5-restarts-in-10-min failed state`
- [ ] `feat(ipc): push sidecar:state-changed to the renderer`
- [ ] `feat(ui): splash and "Restart engine" error screen`
- [ ] `feat(ui): Tailwind tokens (colours, spacing, radius, type scale)`
- [ ] `feat(ui): app shell with sidebar groups and page header`
- [ ] `test(desktop): unit tests for supervisor state transitions`
- [ ] `docs(contracts): IPC contract v1 reviewed and frozen`

### Phase 1 · Core loop (9 Nov – 13 Dec)

- [ ] `feat(ui): API client hooks with TanStack Query over window.ascend.request`
- [ ] `feat(ui): exercise picker with search (Ctrl+K)`
- [ ] `feat(ui): set table with weight/reps/RPE inputs and inline validation`
- [ ] `feat(ui): keyboard flow (Enter completes set, Space rest, Ctrl+Z undo)`
- [ ] `feat(ui): rest timer with toast when window unfocused`
- [ ] `feat(ui): PR toast and PR flag on the set row`
- [ ] `feat(ui): muscle map SVG regions from react-muscle-highlighter paths`
- [ ] `feat(ui): split chest/delts/rhomboids into the 19 ASCEND regions`
- [ ] `feat(ui): heat colours, opacity by intensity, hatching for over`
- [ ] `feat(ui): muscle tooltip (status chip, ES vs target, readiness)`
- [ ] `feat(ui): keyboard navigation and screen-reader labels for regions`
- [ ] `feat(ui): three rings with 900 ms completion animation (reduce-motion aware)`
- [ ] `feat(ui): daily quest card with XP and progress`
- [ ] `feat(ui): history timeline with filters and calendar heatmap`
- [ ] `feat(ui): onboarding steps 1–7 (profile, goal, training, injuries, diet, language)`
- [ ] `feat(ui): food search and meal log (katori/ladle/piece units)`
- [ ] `feat(ipc): events subscribe/push for dashboard.changed`
- [ ] `test(ui): vitest for rings maths and muscle colour mapping`

### Phase 2 · Local AI (14 Dec – 17 Jan)

- [ ] `feat(ui): coach chat thread view with streaming tokens`
- [ ] `feat(ui): "data ARC used" side panel and AI status card`
- [ ] `feat(ui): AI on/off and rules-only toggles in settings`
- [ ] `feat(ui): proposal diff card (Apply / Edit / Keep my plan)`
- [ ] `feat(ui): photo picker and scan job progress`
- [ ] `feat(ui): scan review with boxes, top-3 chips and one-question prompt`
- [ ] `feat(ui): portion unit + oil level controls with live kcal range`
- [ ] `feat(ui): scan failure state with search-and-pick fallback`
- [ ] `feat(ui): injury report flow on the body map`
- [ ] `feat(ui): muscle drill-down with 1–30 day slider and contributing sets`
- [ ] `feat(ui): onboarding hardware check + model download cards`
- [ ] `test(ui): component tests for chips and proposal diff`

### Phase 3 · Ship v1.0 (18 Jan – 7 Feb)

- [ ] `feat(ui): empty/loading/error states pass across all screens`
- [ ] `feat(ui): settings (units, reset hour, language, notifications, quiet hours)`
- [ ] `feat(ui): backup and restore screens`
- [ ] `feat(ui): import Strong/Hevy with dry-run report`
- [ ] `feat(ui): diagnostics page and export bundle button`
- [ ] `feat(desktop): Windows toasts + tray with start-at-login opt-in`
- [ ] `feat(ui): update available banner and install-on-restart` (pair: Gokul)
- [ ] `feat(ui): About page with licences (MIT muscle art, ODbL, INDB/IFCT)`
- [ ] `test(e2e): onboarding → log workout journey` (pair: Gokul)

### Phase 4 · Breadth (8 Feb – 21 Mar)

- [ ] `feat(ui): martial arts round timer and session form`
- [ ] `feat(ui): flexibility routines and ROM test entry`
- [ ] `feat(ui): meditation timers (box, 4-7-8, body scan) with mood before/after`
- [ ] `feat(ui): activity gallery cards with mini body map`
- [ ] `feat(ui): progress photos capture with ghost overlay and compare slider`
- [ ] `feat(ui): morning check-in dialog`
- [ ] `feat(ui): quests & rank page with trials and weekly challenge`
- [ ] `feat(ui): light theme tokens`
- [ ] `test(ui): visual regression baselines for key screens` (pair: Gokul)

### Phase 5 · MLOps loop (22 Mar – 16 May)

- [ ] `feat(ui): model health page (versions, confidence, correction rate)`
- [ ] `feat(ui): export corrections zip with consent text`
- [ ] `feat(ui): shadow-mode indicator (developer setting)`

## Frontend completion check (each phase)

- [ ] Screens work against the real sidecar, not only the mock
- [ ] States checklist done for every new view
- [ ] Keyboard path and reduce-motion verified
- [ ] Work log updated; demo given at the gate
