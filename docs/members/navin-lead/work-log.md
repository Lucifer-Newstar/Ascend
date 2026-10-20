# Navin · Work log

> Dated record of lead / MLOps / release delivery. One row per merged change that is user-visible or
> crosses lanes. Newest at the bottom. Link the PR. Keep it factual: what shipped, not
> what is planned.

| Date | What I shipped | PR / evidence | Notes (handoff, follow-up) |
|---|---|---|---|
| 2026-10-20 | ML pipeline: preprocessing contract, prepare (dedupe/split/test-own), MobileNetV3 training with MLflow, ONNX export + parity + manifest, evaluate (top-1/3, F1, ECE), labels.json check, DVC stages; ML CI workflow with Gokul | PR #12 (`feat/ml-pipeline`) | Runs on synthetic smoke data only; real datasets, licences and the v0 model are still open |
| 2026-10-20 | Release 0.2.0: version bump across desktop/shared/sidecar, build-time app version, CHANGELOG; merged PRs #1-#16 as lead | PR #16 (`release/v0.2.0`) | Tag v0.2.0 on the merge commit |
| 2026-10-20 | Release 0.3.0: merged PR #25 (with the unknown-field check), version bump, CHANGELOG and release notes; corrected unmeasured figures in the work logs and ml/README; release click-through fixes (keyboard scrolling, set-table contrast, chart labels, weigh-in hint); demo seed with weigh-ins, check-ins and timed sessions | PR #26 (`release/v0.3.0`) | Click-through of every screen in dark and light against the sidecar: no console errors, no 4xx/5xx, axe 0 violations. Tag v0.3.0 on the merge commit |
| 2026-10-20 | Motion and interactivity: 3D muscle map (tilt, flip, per-muscle shading, glow, ready-to-train pulse, hover card, Volume view with 1/7/30 days), `GET /muscles/activity`, header XP chip with level-up burst, animated XP bar, count-ups, ring draw-in, set-logged animation, streak flame, skeleton shimmer, page transitions, card hover, Settings → Reduce motion | PR #28 (`feat/ui-motion`) | Click-through in dark and light: no console errors, no 4xx/5xx, axe 0 violations. Frame timing measured in headless Chromium only; check on real Windows hardware |
| 2026-10-20 | Polish pass: first-load focus fix and larger muscle figure (#29), level-up counts from zero (#30), one date style, units on Diet targets, deload copy (#31), Settings groups (#32), onboarding steps and first-steps Dashboard card (#33), lazy-loaded pages, main chunk 407.8 kB to 341.7 kB (#34), Diet small-window layout and named controls (#35), Coach chat a11y and typing dots (#36) | PRs #29-#36 | Checked at 1366x768 and 1024x700 in both themes; Electron (file://) loading of the lazy chunks to be checked on Windows |
