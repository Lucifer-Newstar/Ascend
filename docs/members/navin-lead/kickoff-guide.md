# Kickoff Guide — running the ASCEND team

> **For Navin.** How to run the Phase 0 kickoff (proposed Mon 26 Oct 2026), the weekly
> sync, demos and phase gates. The meeting's agenda and decisions are in
> [planning/kickoff.md](../../planning/kickoff.md); this page is your script.
> Companion: [study-path.md](study-path.md) · [tracker.md](../../planning/tracker.md)

---

## §0. If the meeting is tomorrow (~45 min prep)

1. Read [docs/README.md](../../README.md) and [proposal.md](../../project/proposal.md) §1–6 — 15 min.
2. Memorise the [30-second pitch](#2-the-pitch-30-seconds--2-minutes) below — 5 min.
3. Open the v2 plan's mockups (dashboard, muscle map, meal scan) ready to screen-share — 5 min.
4. Run the v0.1 skeleton once ([local-setup §5](../../development/local-setup.md#5-run-it)) so you can show `/docs` and a logged set — 15 min.
5. Skim each member's README so you can hand out first issues — 5 min.

## 1. Before the kickoff (the week before)

- [ ] Create the GitHub repo (public; Actions are free on standard runners for public repos), invite all three
- [ ] Turn on branch protection for `main` (PR required, 1 approval, status checks once CI exists)
- [ ] Create labels (`area:*`, `phase:*`, `type:*`, `contract`, `good-first-issue`, `needs-owner`, `blocked`) and a Project board (Backlog / Ready / In progress / Review / Done)
- [ ] Commit `docs/` and the code skeleton with honest messages
- [ ] Open the 12 first issues from [kickoff.md §5](../../planning/kickoff.md#5-first-issues-phase-0-week-1)
- [ ] Send the pre-read list (kickoff.md §3) to the group with the meeting time

## 2. The pitch (30 seconds + 2 minutes)

**30 seconds:** "ASCEND is a Windows fitness RPG that runs fully offline. You log
workouts and Indian meals; deterministic engines turn them into XP, quests, ranks and an
anatomical muscle map; a local AI coach explains the numbers and adapts your plan, but
never decides on its own. Nothing leaves your PC."

**2 minutes (architecture):** Electron + React UI → typed IPC bridge → main process
supervises a Python FastAPI sidecar on a random localhost port with a token → SQLite with
migrations → Ollama runs qwen3:4b for the coach and a small vision model for meal photos,
our own ONNX classifier names Indian dishes on the CPU. Rules decide, the model explains,
and the whole app works with AI switched off. We ship it as a normal Windows installer
that auto-updates from GitHub Releases.

## 3. Kickoff script (60–75 min)

| Min | Say / do | Output |
|---|---|---|
| 0–10 | Pitch + mockups; "what it is NOT": no cloud, no accounts, no mobile app, no medical advice | Shared picture |
| 10–20 | Architecture diagram from [system-architecture.md §3](../../architecture/system-architecture.md#3-processes); show the skeleton's `/docs` | Everyone knows the boundaries |
| 20–30 | Roles from [team-structure.md](../../team/team-structure.md); ask each: "does this lane fit you?" | Owners confirmed |
| 30–45 | Decisions D1–D10 and K1–K8; disagreements get 3 minutes, then you decide and log | Decision-log rows |
| 45–55 | Working rules: commits, branches, PR template, **AI-assistance rule** ("you can use it; you must explain it") | Rules accepted |
| 55–65 | Each member takes their 3 first issues and books 2 h for machine setup | Issues assigned |
| 65–75 | Sync slot, gate date (8 Nov), hardware table in the tracker | Calendar set |

**Say it plainly once:** every commit is dated when it is written; nobody squashes
someone else's work into their own; the history is the evidence for everyone's CV.

## 4. Weekly sync (30 min, proposed Sunday 7:30 PM IST)

```text
1. Tracker walk (5)        — you read statuses aloud, flip what changed
2. Demo of the week (12)   — each member, 3 min, from their own machine
3. Blockers (8)            — one owner + next step per blocker
4. Next week (5)           — each member names 2–4 tasks from their phase plan
```

After the sync (10 min, you): update [tracker.md](../../planning/tracker.md), log
decisions in [planning/README.md](../../planning/README.md#2-decision-log), add a work-log
line if you shipped something.

## 5. Demo-of-the-week rules

- Show it running, not slides. A failing test you are fixing counts.
- Say which task(s) from your phase plan it closes.
- One question from the team each — practice for interviews.

## 6. Phase gate review (45 min, last sync of a phase)

1. Run the gate demo from a **CI-built installer** ([phases.md §1](../../planning/phases.md#1-phase-overview)).
2. Walk the gate checklist ([phases.md §2](../../planning/phases.md#2-gate-checklist-every-phase)).
3. Read the gate metrics ([evaluation.md §3](../../operations/evaluation.md#3-gate-usage)).
4. Each member explains one thing they built (teach-back).
5. Decide: pass / pass with carry-over (logged) / repeat next week.
6. Re-plan the next phase with the cut order if behind.

## 7. When things go wrong

| Situation | What you do |
|---|---|
| Someone silent for a week | Message privately first; offer to swap a task; re-label issues `needs-owner` after two weeks |
| Two members disagree on an interface | 10-minute call, you decide, write it in the contract PR |
| Behind schedule | Apply the cut order ([phases.md §6](../../planning/phases.md#6-cut-order)); never cut the release pipeline |
| `main` is red | Gokul fixes or reverts the same day; nobody merges on red |
| Exams | Announce two weeks ahead; shift the timeline; log it |
