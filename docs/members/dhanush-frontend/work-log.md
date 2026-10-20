# Dhanush · Work log

> Dated record of frontend / Electron delivery. One row per merged change that is user-visible or
> crosses lanes. Newest at the bottom. Link the PR. Keep it factual: what shipped, not
> what is planned.

| Date | What I shipped | PR / evidence | Notes (handoff, follow-up) |
|---|---|---|---|
| 2026-10-20 | Component test setup (Testing Library + jsdom), light theme tokens, units helpers, preferences context, Settings: theme / units / training days | PR #8 (`feat/ui-foundation`) | Everyone: `*.test.tsx` now runs in jsdom; use `usePrefs()` for units in new screens |
| 2026-10-20 | Training page with 6 section tabs on one logger; timed set form (duration, distance, HR); kg/lb in the logger; inline set edit/delete | PR #9 (`feat/ui-activity`) | Live round/meditation timers are the next step |
| 2026-10-20 | Progress page: weight trend chart + weigh-in, goal ETA with goal editing, 8-week volume/sessions/minutes bars, PR list, tape measurements; SVG chart helpers; two fixes found clicking through against the real sidecar (axis overflow, aborted 204s) | PR #11 (`feat/ui-progress`) | Checked in a headless browser in dark and light, kg and lb |
| 2026-10-20 | Muscle drill-down (1/7/30 days, contributing sets), morning check-in card, weekly review + deload cards on Coach; caught a misleading check-in note, fixed by Jegatheesan in PR #13 | PR #14 (`feat/ui-insights`) | Checked in a headless browser against the sidecar |
| 2026-10-20 | States pass: skeletons per screen, offline-aware ErrorState, stale-data notice, history empty-state actions, diet no-match state, coach retries; fixed history showing runs as \"1 reps\" | PR #18 (`feat/ui-states`) | useApi now exposes `status` (0 = engine unreachable) |
| 2026-10-20 | Import & export page: Strong/Hevy preview-then-import with report card, FileDrop, exports moved off Settings; History shows imported sessions; Back/Forward now switch pages | PR #21 (`feat/ui-data`) | Clicked through against the real sidecar: preview → import → History badge → duplicate re-import reports 0 new |
| 2026-10-20 | Accessibility pass: AA text/status tokens in both themes, skip link + focus to page heading, window titles, Ctrl+1…8, Enter logs a set, Esc closes drill-down, assertive error toasts, chart data tables, reduced motion, keyboard-reachable muscles, axe-core in component tests | PR #24 (`feat/ui-a11y`) | axe-core with contrast on all 8 pages × 2 themes: 0 violations after the fix. Before it, about 70 failing nodes in the dark theme; no light-theme baseline was captured |
