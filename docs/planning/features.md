# Features — Locked Scope

> **Design record, not a description of the shipped app.** Written to plan the build; where it
> differs from the code, the [README](../../README.md) and the [CHANGELOG](../../CHANGELOG.md) describe what
> ASCEND 1.1.0 actually does.

> **What ASCEND builds, in which release, who leads it, and how it is accepted.**
> Source: ASCEND plan v2 §03 "What ships when". Releases: **v1.0** = MVP (~7 Feb 2027,
> estimate), **v1.1** = within ~6 weeks after, **Later** = real but optional.
> Changing this table needs a decision-log row ([README §2](README.md#2-decision-log)).
>
> Lead = the member accountable for the feature end to end (others contribute).
> D = Dhanush (frontend) · J = Jegatheesan (backend) · G = Gokul (DevOps) · N = Navin (lead).

---

## 1. MVP — v1.0

| ID | Feature | Lead | Acceptance (all must pass) |
|---|---|---|---|
| **T1** | Shared workout logger for Gym, Calisthenics, Cardio | J (API) / D (UI) | Log a session with sets (weight, reps, RPE) or cardio (time, distance, RPE); edit/delete; undo (Ctrl+Z); keyboard flow Enter/Space works |
| **T2** | Rest timer | D | Auto-starts after a set; toast when window unfocused; per-exercise default |
| **T3** | PR detection | J | e1RM (Epley default, Brzycki option) for 1–10 reps; rep-PR above 12; warm-ups excluded; one PR per type per exercise per session; >10% jump asks to confirm. Golden tests pass |
| **T4** | History | D / J | One timeline with filters (section, muscle, date), calendar heatmap, daily kcal in/out; editing a past set re-runs PR/XP/load through events |
| **T5** | Adaptive planner, progressive overload, deloads | J | Split by days/week; double progression + RPE rule; 3+1 deload blocks; missed-session rules; every change is a diff the user applies |
| **D1** | Three rings + completion animation | D | Daily tasks, kcal eaten, kcal burned (labelled estimate); 900 ms animation when all three close; respects reduce-motion |
| **D2** | Anatomical muscle map + drill-down | D (UI) / J (load engine) | 19 regions front/back; colours under/optimal/recovering/over + hatching; tooltip; drill-down 1 D → 30 D with daily bars, recovery curve, contributing sets; set logged → map updated < 150 ms (target) |
| **D3** | Dashboard quest card + coach notice | D | Today's quest with XP; rule-based proposal card with Apply / Edit / Keep my plan |
| **G1** | XP, levels, stat points | J | XP table + curve `round(100 × L^1.3)`, streak bonus ≤ ×1.3, daily cap 600; points steer quests only |
| **G2** | Daily quests, humane penalties, streak freezes | J | Generated at reset time (default 4 AM); sized by last-7-day completion; missed day → ≤10-min recovery quest, never XP loss; freezes earned/held/auto-used; sick/injury/travel/exam modes |
| **G3** | Ranks E → C | J / D | Level bands; rank shown in header; trials are placeholders until v1.1 |
| **N1** | Indian food search, portions, saved meals | J | INDB + IFCT + Open Food Facts India subset imported with licences; katori/ladle/cup/piece/tbsp units; oil level; thali mode; saved meals; nutrients only from DB |
| **N2** | Meal photo scan + corrections | J (pipeline) / N (classifier) / D (UI) | ONNX classifier first (whole photo + tapped items) → top-3 → portion → DB lookup; optional qwen3-vl:2b second opinion ([ADR-0012](../architecture/adr/0012-classifier-first-meal-scan.md)); ≥0.80 pre-selected, <0.65 asks one question; every edit stored as a correction; 60 s timeout → search-and-pick fallback; details in [ai/food-recognition.md](../ai/food-recognition.md) |
| **C1** | Coach: plan generation | J | Rules produce the plan; the LLM explains it; works with AI off (templates) |
| **C2** | Injury protocol | J | Red-flag triage bypasses the model; restrictions → substitutions → return-to-load steps; "not a medical device" shown |
| **C3** | Weekly review (every 7th day) | J | Rule findings scored, top 3 → plan diffs; LLM writes a 3-sentence summary from given numbers; template with AI off |
| **C4** | Coach chat in English, Tamil beta | J (backend) / D (UI) | Streaming over SSE; tool calls create proposals only; "Show in English" under non-English replies; Tamil marked beta until tested on 30 questions; every reply validated ([ADR-0011](../architecture/adr/0011-prompt-contracts-and-output-validation.md)) |
| **C5** | AI-off / rules-only mode, override, plan import | J / D | A single toggle disables all model calls; user plan via CSV template wins over the planner |
| **C6** | Rule-based tip cards in each section | J / D | Volume spike, imbalance, missed sessions, PR stall, low protein; "why?" asks the LLM to rephrase |
| **P1** | Body weight trend + ETA to goal | J / D | 7-day average; ETA as a range with confidence; "not on track" with reason instead of a date |
| **X1** | Onboarding + hardware check | D / J | ~5 minutes; profile, goal, training, injuries on body map, diet, language, hardware check picks AI tier (or off), optional baseline, first-week plan |
| **X2** | Backup, CSV/JSON export, diagnostics | J / D | `.ascendbak` with manifest SHA-256; daily auto-backup (7 daily + 4 weekly); scrubbed diagnostics zip |
| **X3** | Strong / Hevy CSV import | J (adapters) / G (CI fixtures) | Golden-file fixtures (anonymised real exports) pass, including Strong's Oct 2025 format change |
| **X4** | Desktop notifications | D | Windows toasts; quiet hours 22:00–07:00; max 3/day; each type switchable; tray opt-in |
| **X5** | Installer + auto-update | G | NSIS per-user installer; electron-updater from GitHub Releases (stable/beta); checksums + SBOM attached |
| **M1** | Model manager | J / N | Manifest (name, version, URL, SHA-256, size, licence, min VRAM); resumable verified downloads; tier selection; fallbacks table implemented |

## 2. v1.1 (Phase 4, ~8 Feb – 21 Mar 2027, estimate)

| ID | Feature | Lead | Notes |
|---|---|---|---|
| T6 | Martial arts section | D / J | Round timer, session types, rounds × shoulder/core load, AGI XP |
| T7 | Flexibility section | D / J | Holds, monthly ROM tests, FLX stat, mobility quests |
| T8 | Meditation section | D / J | Box 4-4-4-4, 4-7-8, body scan; mood before/after; separate calm streak |
| T9 | Activity Gallery with demos | D | MVP ships a basic list; v1.1 adds demo media, mini body map, cues, history |
| G4 | Trials, weekly challenges, bosses, titles | J / D | Original naming; scaled by age, body weight, injury flags |
| P2 | Progress photos + measurements | D / J | Guided capture with ghost overlay; encrypted when encryption is on; side-by-side compare; no AI judging |
| P3 | 20-second morning check-in → readiness | J / D | Weights are estimates; skipping changes nothing |
| N3 | Adaptive calorie target from weight trend | J | Adherence-neutral, max ±150 kcal per weekly change, needs ≥4 weigh-ins/week |
| X6 | Optional encryption (SQLCipher + AES-256-GCM photos) | J / G | Key in Windows DPAPI via Electron safeStorage; printed recovery code |
| X7 | Light theme | D | Same tokens, swapped surfaces |
| C7 | Tamil chat out of beta | N / J | Only if the 30-question test passes; else English + IndicTrans2 fallback |

## 3. Later (not scheduled)

| ID | Feature | Notes |
|---|---|---|
| L1 | Retraining from corrections (MLOps loop) | Phase 5 (Mar–May 2027), lead N |
| L2 | Wearable file import (GPX / FIT / Health Connect / Apple Health export) | File import only; no live sync without a phone |
| L3 | Barcode scan (webcam) against local Open Food Facts | ODbL attribution |
| L4 | Webcam form feedback (MediaPipe Pose) | Research spike first |
| L5 | Voice input (faster-whisper) | CPU model size/speed unverified |
| L6 | Ghost races against your own past weeks | Replaces leaderboards |
| L7 | Female body figure for the muscle map | Same MIT package has one |

## 4. Cut or replaced

| Was | Now | Why |
|---|---|---|
| Online guilds and leaderboards | Ghost races (L6) | Need a server; ASCEND has none |
| AI analysis of progress photos | Side-by-side compare + pose overlay | Small local VLMs can't judge body change reliably; a wrong verdict does harm |
| A separate AI panel in every section | Rule-based tip cards (C6); LLM only on "why?" | Cheaper, testable, works with AI off |
| Stat points that change strength numbers | Stats from real data; points steer quests | Points must not fake progress |
| Llama 3.2 3B as coach | qwen3:4b | Llama 3.2 lists 8 languages, Tamil not among them; text-only |
| PR as its own subsystem | Records view inside Progress (sidebar tab kept) | One place for all numbers |

## 5. Non-functional requirements

| ID | Requirement | Target (estimate until measured) |
|---|---|---|
| NF1 | Cold start to dashboard | < 4 s on the reference laptop |
| NF2 | Set logged → map/XP updated | < 150 ms |
| NF3 | Coach first token | < 3 s warm; fallback to rules if > 20 s |
| NF4 | Meal scan end to end | 5–15 s |
| NF5 | Works with AI off | 100% of v1.0 features usable |
| NF6 | Data safety | Backup before every migration; restore tested in CI |
| NF7 | Privacy | Zero network calls except opt-in model download + update check (tested) |
| NF8 | Accessibility | Keyboard-only path for logging; reduce-motion respected; colour never the only signal |

Reference laptop: Windows 11, Ryzen 7 7435HS, 12 GB RAM, RTX 3050 Laptop 4 GB VRAM.
