# Jegatheesan · Backend Phase Plan

> **Purpose:** my delivery, handoffs and commit-sized tasks by phase. Shared scope: [features](../../planning/features.md). Gates: [phases](../../planning/phases.md). Dates (estimates): [timeline](../../planning/timeline.md). Tick a box when the commit is merged. AI tasks and their design docs: [ai-roadmap](../../ai/ai-roadmap.md).

| Phase | I deliver | I need | Handoff / completion check |
|---|---|---|---|
| **0 · Foundations** | Contracts reviewed, sidecar hardened (health detail, shutdown), WAL + migration baseline, Prism mock | Launch protocol (exists) | `/health` reports db + migration head; mock serves every contract |
| **1 · Core loop** | Workouts, PRs, muscle load v1 (ES + readiness), XP/quests/streaks/ranks, food import, outbox, SSE | Formula specs from Navin | Gate demo: set → PR → XP → map via events; edit a set re-computes |
| **2 · Local AI** | Job queue, model manager, Ollama client + fallbacks, coach rules, injury flow, scan pipeline, weekly review | Classifier ONNX from Navin | Scan → corrections stored; AI off → rules answers; number-fidelity check passes |
| **3 · Ship v1.0** | Backup/restore, CSV/JSON export, Strong/Hevy import, diagnostics bundle | Golden fixtures job from Gokul | Restore round-trip test; import fixtures pass |
| **4 · Breadth** | Section engines (martial arts, flexibility, meditation), trials/challenges, readiness, adaptive TDEE, encryption | — | New sections feed XP/load/history |
| **5 · MLOps loop** | Prediction logging, corrections export, shadow-mode switch | Retrained model from Navin | Shadow predictions logged without being shown |

## Commit-sized tasks

### Phase 0 · Foundations (26 Oct – 8 Nov)

- [x] `feat(core): /health reports db status and alembic head`
- [x] `feat(core): POST /shutdown checkpoints WAL before exit`
- [x] `feat(core): verify WAL, foreign_keys and busy_timeout pragmas on connect` — pragmas set in the skeleton's engine; /health now reports journal_mode and db status
- [x] `test(core): token and Host middleware reject bad requests`
- [ ] `docs(contracts): review module YAMLs with Dhanush, freeze core paths`
- [ ] `chore(sidecar): npm run mock script for Prism`
- [x] `refactor(core): typed event classes with version field`
- [ ] `refactor(coach): move the v0 system prompt into prompts/ with registry.yaml`
- [ ] `test(coach): fake Ollama server fixture (normal, slow, error streams)`

### Phase 1 · Core loop (9 Nov – 13 Dec)

- [x] `feat(workouts): list workouts with pagination`
- [x] `feat(workouts): edit and delete a set with SetUpdated event`
- [ ] `feat(workouts): PR types (e1RM, rep PR, volume) with typo guard`
- [ ] `feat(workouts): double progression and RPE load rule`
- [x] `feat(workouts): deload triggers (planned 3+1 and reactive)`
- [ ] `feat(progress): effective sets with mapping weights and effort(RPE)`
- [ ] `feat(progress): fatigue decay and readiness per muscle`
- [ ] `feat(progress): muscle_load_daily projection with algo_version`
- [x] `feat(progress): muscle history endpoint for drill-down`
- [ ] `feat(gamification): level curve, streak bonus and daily cap`
- [ ] `feat(gamification): quest generation at reset hour, sized by completion`
- [ ] `feat(gamification): streak freezes and pause modes`
- [ ] `feat(gamification): ranks E–C by level band`
- [ ] `feat(nutrition): INDB recipe import with licence column`
- [ ] `feat(nutrition): IFCT raw foods + Open Food Facts India subset import`
- [ ] `feat(nutrition): portion units and oil level`
- [x] `feat(core): transactional outbox + dispatcher with replay on start` — worker's first pass at start-up delivers anything left pending
- [x] `feat(core): processed_events for idempotent handlers`
- [x] `feat(core): SSE /events with Last-Event-ID`
- [ ] `test(progress): golden files for load model v1`
- [ ] `test(workouts): Hypothesis tests for e1RM and progression`
- [ ] `feat(coach): facts block formatters with fact ids`
- [ ] `feat(coach): intent router keyword lists (English, Tamil, Tanglish)`
- [ ] `feat(nutrition): portions table with a source column`

### Phase 2 · Local AI (14 Dec – 17 Jan)

- [ ] `feat(core): jobs table with GPU and CPU workers`
- [ ] `feat(core): job timeouts, retries, cancel and progress events`
- [ ] `feat(ai): model manifest loader and tier selection`
- [ ] `feat(ai): resumable download with SHA-256 verify and atomic rename`
- [ ] `feat(ai): Ollama client with streaming and first-token timeout`
- [ ] `feat(ai): GPU lock with keep_alive unload/reload around VLM jobs`
- [ ] `feat(ai): fallbacks table (AI off, missing, slow, OOM, Ollama down)`
- [ ] `feat(coach): planner rules (split, volumes, 48/72 h spacing)`
- [ ] `feat(coach): red-flag routing in English, Tamil and transliteration`
- [ ] `feat(coach): injury restrictions, substitutions and return-to-load`
- [ ] `feat(coach): proposals table and apply/keep endpoints`
- [ ] `feat(coach): chat endpoint streaming over SSE`
- [x] `feat(coach): weekly review findings and top-3 diffs`
- [ ] `feat(coach): number-fidelity check with template fallback`
- [ ] `feat(nutrition): ONNX classifier top-3 via onnx_runtime` (pair: Navin)
- [ ] `feat(nutrition): confidence thresholds and corrections table`
- [ ] `bench(ai): tokens/s and VRAM for candidate models` (pair: Navin)
- [ ] `test(ai): Ollama client against a fake server`
- [ ] `feat(coach): prompt registry rendered with Jinja2 StrictUndefined`
- [ ] `feat(coach): JSON-schema output via Ollama format + jsonschema check`
- [ ] `feat(coach): eating-disorder, diagnosis and medicine filters with fixed replies`
- [ ] `feat(coach): sentence-gated streaming with validators`
- [ ] `feat(coach): propose_plan_change tool without numeric arguments`
- [ ] `feat(coach): token budget trimming + prompt_eval_count logging`
- [ ] `feat(ai): refuse a non-loopback OLLAMA_HOST`
- [ ] `feat(ai): /api/ps check and partial-offload status`
- [ ] `feat(nutrition): classifier-first scan (whole photo + tapped items)`
- [ ] `feat(nutrition): VLM second-opinion job with GPU handover`
- [ ] `feat(nutrition): personal swaps from corrections`

### Phase 3 · Ship v1.0 (18 Jan – 7 Feb)

- [ ] `feat(io): move export endpoints into the io module (paths unchanged)`
- [ ] `feat(io): .ascendbak backup with manifest SHA-256`
- [ ] `feat(io): restore with schema-version check`
- [ ] `feat(io): Strong CSV adapter (both header variants)`
- [ ] `feat(io): Hevy CSV adapter`
- [ ] `feat(io): plan CSV import template`
- [ ] `feat(core): automatic backup before migrations, restore on failure`
- [ ] `feat(core): diagnostics bundle with scrub allow-list`
- [ ] `test(io): golden fixtures for every import/export format` (pair: Gokul)
- [ ] `feat(ai): unload loaded models on app quit (keep_alive 0)`
- [ ] `fix(coach): tune timeouts from beta latency data`

### Phase 4 · Breadth (8 Feb – 21 Mar)

- [x] `feat(workouts): martial arts sessions and time-based muscle load` — also cardio; load-time-v1
- [x] `feat(workouts): flexibility holds and ROM tests` — holds done; ROM tests deferred to v1.1
- [x] `feat(workouts): meditation sessions and calm streak`
- [ ] `feat(gamification): trials, weekly challenges and bosses`
- [x] `feat(progress): morning check-in and readiness score`
- [ ] `feat(nutrition): adaptive TDEE from trend weight`
- [x] `feat(progress): ETA range with confidence`
- [ ] `feat(core): optional SQLCipher encryption` (pair: Gokul for packaging)
- [ ] `feat(ai): IndicTrans2 path B prototype on CPU (int8)`
- [ ] `feat(coach): readiness note after the morning check-in`

### Phase 5 · MLOps loop (22 Mar – 16 May)

- [ ] `feat(ai): log prediction and confidence per scan`
- [ ] `feat(nutrition): corrections export (zip, consent flag)`
- [ ] `feat(ai): shadow-mode second classifier`
- [ ] `feat(ai): model-only update switch from manifest`
- [ ] `feat(nutrition): crops-only option in the corrections export`
- [ ] `feat(ai): keep the previous classifier and roll back on a failed load`

## Backend completion check (each phase)

- [ ] Contract matches code (drift job green)
- [ ] New formulas have golden tests and an `ALGO_VERSION`
- [ ] Migration tested from fixture DBs
- [ ] Work log updated; demo given at the gate
