# Timeline

> **Design record, not a description of the shipped app.** Written to plan the build; where it
> differs from the code, the [README](../../README.md) and the [CHANGELOG](../../CHANGELOG.md) describe what
> ASCEND 1.1.0 actually does.

> **All dates are estimates**, assuming each member gives ~8–10 hours a week (estimate)
> around final-year coursework. Exam weeks are not yet known — the lead adjusts this
> page once the semester calendar is out. Phases: [phases.md](phases.md).

---

## 1. Calendar

```mermaid
gantt
    title ASCEND — estimated calendar (Oct 2026 → May 2027)
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    section Phases
    0 Foundations        :p0, 2026-10-26, 14d
    1 Core loop          :p1, 2026-11-09, 35d
    2 Local AI           :p2, 2026-12-14, 35d
    3 Ship v1.0          :p3, 2027-01-18, 21d
    4 Breadth v1.1       :p4, 2027-02-08, 42d
    5 MLOps loop v1.2    :p5, 2027-03-22, 56d
    section Milestones
    Kickoff              :milestone, m0, 2026-10-26, 0d
    v0.1 hello installer :milestone, m1, 2026-11-08, 0d
    v0.3 core loop       :milestone, m2, 2026-12-13, 0d
    v0.6 local AI        :milestone, m3, 2027-01-17, 0d
    v1.0 MVP             :milestone, m4, 2027-02-07, 0d
    v1.1                 :milestone, m5, 2027-03-21, 0d
    v1.2                 :milestone, m6, 2027-05-16, 0d
```

## 2. Week by week to v1.0

| Week of | Phase | Focus (all lanes) |
|---|---|---|
| 26 Oct | 0 | Kickoff, repo, rules, contracts draft, machine setup |
| 2 Nov | 0 | Shell + sidecar + migration; CI; first installer artefact (v0.1) |
| 9 Nov | 1 | Freeze core contracts; logger API + UI; event bus |
| 16 Nov | 1 | PRs, History; muscle-load projector; DVC + MLflow up |
| 23 Nov | 1 | Muscle map component; XP/levels; coverage + drift gates |
| 30 Nov | 1 | Quests, streaks, freezes; food DB import; photo collection |
| 7 Dec | 1 | Rings, onboarding; baseline classifier; gate demo (v0.3) |
| 14 Dec | 2 | Job queue, model manager; model benchmarks |
| 21 Dec | 2 | Ollama client + fallbacks; coach planner; classifier training |
| 28 Dec | 2 | Injury flow; chat UI with streaming; ONNX export + parity |
| 4 Jan | 2 | Scan pipeline + chips UI; eval gate job |
| 11 Jan | 2 | Weekly review; Tamil 30-question test; gate demo (v0.6) |
| 18 Jan | 3 | Release workflow; backup/restore; states pass |
| 25 Jan | 3 | Auto-update channels; Strong/Hevy import; diagnostics |
| 1 Feb | 3 | Packaged smoke tests, rollback drill, release notes → **v1.0 (~7 Feb)** |

## 3. Expected hours per member (estimate)

| Phase | Weeks | Dhanush | Jegatheesan | Gokul | Navin |
|---|---|---|---|---|---|
| 0 | 2 | 16 | 16 | 20 | 20 |
| 1 | 5 | 45 | 50 | 35 | 40 |
| 2 | 5 | 40 | 50 | 30 | 45 |
| 3 | 3 | 25 | 25 | 30 | 30 |
| **To v1.0** | **15** | **~126** | **~141** | **~115** | **~135** |

The backend lane is the heaviest; if it slips, Navin takes the `io` adapters and Gokul
takes diagnostics bundling (decision-log row required).

## 4. After v1.0

Phases 4–5 overlap placement interviews (Feb–Apr 2027). Hours drop to ~5–6 a week each
(estimate); the cut order in [phases.md §6](phases.md#6-cut-order) applies first to v1.1 items.
