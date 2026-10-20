# Adaptive Planning and the AI

> Which parts of workout planning are rules, which parts are AI, and how a suggestion
> becomes a change only when the user says yes. Covers the planner, progression, deloads,
> the weekly review, injury adaptation and the morning readiness check-in.
> Owner: **Jegatheesan** (engines, proposals); formula specs: **Navin**; UI: **Dhanush**.
> Principle: [ADR-0005](../architecture/adr/0005-deterministic-engines-llm-explains.md).

---

## 1. Status

| Piece | Status |
|---|---|
| Muscle load and recovery engine (effective sets, decay, readiness, status under / optimal / recovering / over) | **implemented** (v0.1, `progress/muscle_load.py`) |
| XP, levels, daily quest by rules, streak with freeze, ranks | **implemented** (v0.1, `gamification/`) |
| Rule tips (`coach-rules-v1`) that react to load and nutrition | **implemented** |
| Planner, progression, deloads, missed-session rules | deload triggers **implemented** (`deload-v1`); planner and progression planned · Phase 1 |
| Proposals (Apply / Edit / Keep my plan) and the `propose_plan_change` tool | planned · Phase 2 |
| Weekly review findings, diffs and summary | planned · Phase 2 |
| Injury protocol | planned · Phase 2 |
| Morning check-in and readiness score | **implemented** (`readiness-v1`, `POST /checkins`) |

---

## 2. Rules vs AI

| Job | Rules engine (decides, computes every number) | Language model (optional; words only) |
|---|---|---|
| Plan generation | Split by days per week, weekly sets per muscle, exercise choice from equipment and injury flags, 48 h spacing (72 h for quads, hamstrings, lower back), session length cap | `P-06` explains the plan day by day |
| Progressive overload | Double progression, RPE rule (±5% clamp), calisthenics ladders, cardio +10% per week max, stall detection | "Why?" on a progression (`P-04`) |
| Deloads | Planned 3 + 1 blocks; reactive deload when two of four signals are true ([§5.1](#51-reactive-deload-signals-deload-v1)) | `P-07` one-line reason on the proposal |
| Missed sessions | Move within 48 h, else drop and redistribute up to +2 sets per remaining session, never > 1.5 × planned volume | Encouraging wording in chat |
| Weekly review | Collect, score findings, pick the top 3, turn each into a plan diff | `P-05` three-sentence summary |
| Injury adaptation | Red-flag triage, blocked patterns, substitutions, duration, return-to-load, escalation | `P-08` kind wording and one follow-up question |
| Readiness check-in | Score from four inputs, band, effect on today's quest | `P-09` one sentence |
| Calorie target | TDEE (Mifflin-St Jeor, estimate) now; adaptive TDEE from trend weight in Phase 4; floors | Explains the change, never sets it |
| Tip cards in every section | Volume spike, imbalance, missed sessions, PR stall, low protein | `P-03` rephrase, `P-04` "why?" |
| Chat requests ("make Thursday shorter") | Planner checks a rule allows it and computes the diff | Recognises the request and calls `propose_plan_change` |

With AI off every row still works: the right-hand column is replaced by templates
([coach-llm.md §9](coach-llm.md#9-the-rule-based-fallback)).

---

## 3. The proposal: the only way a plan changes

```text
trigger (weekly review | reactive deload | injury | chat tool | tip card "fix it")
   → planner computes a diff + checks the rule that allows it
   → proposals row: kind, diff, reason_code, source, algo_version, status = pending
   → reason text: P-07 (AI on) or template (AI off), number-checked
   → card: [Apply] [Edit] [Keep my plan]
         Apply → plan updated, PlanChanged event, XP/quests recomputed
         Edit  → user changes the diff (within rule limits), then applies
         Keep  → status kept; same diff not re-proposed for 7 days
   → pending for 7 days without an answer → status expired (no change)
```

| Field | Values |
|---|---|
| `kind` (contract) | `plan_change`, `deload`, `kcal_target`, `injury_protocol` |
| `source` | `weekly_review`, `reactive_deload`, `injury`, `chat_tool`, `tip_card` |
| `status` | `pending`, `applied`, `edited`, `kept`, plus `expired` (planned addition) |
| `algo_version` | The planner version that computed the diff ([data-model.md §5](../architecture/data-model.md#5-migration-rules)) |

**Changes need my approval** is on by default. The optional **auto-apply small changes**
setting covers only ±1 set on one exercise and load tweaks inside the progression rule; it
never covers deloads, calorie changes, injury protocols or anything the model proposed.

**Your plan wins:** if the user imported or built their own plan, the planner switches to
suggest-only for it: proposals are still shown, nothing is auto-applied, and the weekly
review never rewrites the plan's structure.

---

## 4. What the AI may suggest

The model can only **ask the planner** for a change through `propose_plan_change`
(`S-TOOL-PROPOSE` in [prompt-library.md](prompt-library.md#5-output-schemas)). The tool has no
numeric arguments.

| Tool `kind` | Example user request | What the planner does | Allowed when |
|---|---|---|---|
| `add_sets` | "Can I do more chest?" | +2 sets for the muscle (rule range +2 to 4) | Muscle under target and readiness ≥ 0.70 |
| `remove_sets` | "Today's too long" | Removes the overlapping accessory first | Always (shortening is always safe) |
| `swap_exercise` | "I don't have a barbell today" | Same primary muscle, allowed pattern, available equipment, lowest joint stress | A substitute exists in the library |
| `move_session` | "I can't train Thursday" | Moves within 48 h or drops and redistributes | Missed-session rule allows it |
| `deload` | "I feel beaten up all week" | Proposes the deload week | Two of the four reactive signals are true, or the user explicitly asks (then marked user-requested) |
| `kcal_target` | "Should I eat more?" | ±150 kcal per the weekly-review rules | A weight-trend finding supports it; never below the floor |

The model may **not**:

- set or mention a load, rep target, calorie value or date that is not in the facts;
- add an exercise that is not in the library or whose movement pattern is blocked;
- propose anything during an active red-flag injury (the tool is disabled for that area);
- claim a change has been made (validator V4).

If no rule supports a request, the tool answers `accepted: false` with the rule code and the
model explains, for example, that hamstrings are still recovering until Wednesday.

---

## 5. The weekly review (every 7th day)

Runs as a background job on the user's 7th day from their plan start (default Sunday, the
"Weekly review ready" notification at 8 PM), with a 120 s budget.

1. **Collect** the last 7 days and the 4 weeks before: sessions done vs planned, effective
   sets per muscle vs target, e1RM slope of key lifts, 7-day average weight vs goal pace, kcal
   and protein adherence, pain flags, quest completion.
2. **Score findings** with fixed rules:

   | Code | Condition | Severity | Diff |
   |---|---|---|---|
   | `PAIN_ACTIVE` | An injury protocol is active | 4 | None; keep the protocol |
   | `ADHERENCE_LOW` | Sessions done < 70% of planned, two weeks running | 3 | Shorten sessions or drop a training day |
   | `WEIGHT_FAST_GAIN` | Lean bulk and 7-day average rising > 0.5% of body weight per week | 3 | −150 kcal |
   | `DELOAD_DUE` | Two of the four reactive deload signals | 3 | Deload week |
   | `WEIGHT_STALL` | Lean bulk and < 0.1 kg per week for 2 weeks | 2 | +150 kcal |
   | `MUSCLE_UNDER` | Muscle under its weekly target 2 weeks running | 2 | +2 to 4 sets |
   | `MUSCLE_OVER` | Muscle over its weekly range | 2 | Remove the overlapping accessory |
   | `E1RM_FLAT` | No e1RM gain on a key lift for 3 weeks | 1 | New variation or rep range |
   | `PROTEIN_LOW` | Protein under target on ≥ 4 of 7 days | 1 | None; tip card only |

   Cut and maintain goals use the matching energy rules in the energy spec (Navin, Phase 1).
3. **Pick the top 3** by severity (ties: most recent data first) and turn each into a
   proposal (§3).
4. **Write it up:** `P-05` writes three sentences from the findings and facts; it is given the
   numbers and may not change them (V3). AI off or a failed check → template.
5. **The user decides:** apply all, pick some or keep the plan. Reading the review earns
   20 XP.

### Worked example (sample data)

Findings: `MUSCLE_UNDER` (chest, 6 and 7 effective sets vs target 10–20),
`WEIGHT_STALL` (+0.05 kg per week for 2 weeks on a lean bulk), `E1RM_FLAT`
(bench press e1RM 88.7 kg for 3 weeks).

| Version | Text |
|---|---|
| Model (`P-05`, example of an acceptable output) | "You trained 4 of 4 planned days this week, nice consistency. Your chest is still under its weekly target, and your weight has barely moved for two weeks. The changes below add chest sets and a little more food so the bulk keeps moving." |
| Template (AI off) | "This week: 4 of 4 sessions done. Main finding: chest is below its weekly target (6 effective sets; target 10–20). Proposed: more chest sets, a calorie increase and a new bench variation; review each below." |

Every number in both versions is present in the findings or facts.

### 5.1 Reactive deload signals (deload-v1)

Implemented in `services/sidecar/app/modules/workouts/deload.py` and served by `GET /deload`.
A reactive deload is recommended when **two or more** hold:

| Signal | Condition |
|---|---|
| `LOW_READINESS` | ≥ 3 check-ins in the last 7 days with an average readiness < 50 |
| `HEAVY_SORENESS` | Soreness "a lot" on ≥ 3 of the last 7 check-ins |
| `PERFORMANCE_DROP` | ≥ 2 key lifts (squat, bench, deadlift, overhead press) whose best e1RM in the last 14 days is ≥ 3 % below their best in the 21 days before |
| `FATIGUE_BUILDUP` | ≥ 3 muscles over their weekly range or under 50 % readiness |

The planned deload is due after 3 consecutive training weeks (≥ 2 finished sessions each) since
the last accepted deload (`POST /deload/start`). The thresholds are coaching rules of thumb
chosen for the MVP, not validated cut-offs; tune them with beta data and bump `deload-v1`.

### 5.2 Implementation status

`review-v1` (`app/modules/coach/weekly_review.py`, `GET /coach/weekly-review/latest`) implements
every finding in the table above except `PAIN_ACTIVE`, which waits for the injury module.
Planned sessions come from the `sessions_per_week` setting (default 3). Adherence is only judged
once there are two full weeks of history. The summary is the template; the `P-05` model rewrite
plugs in behind the number-fidelity check.

---

## 6. Injury adaptation

| Step | Rule (engine) | AI's part |
|---|---|---|
| 1. Report | From chat, the "I'm hurt" button or a pain score after a set: area on the body map, side, type (dull / sharp / tingling), pain 0–10, when | Chat may route here when the router sees `pain` |
| 2. Red-flag triage | Sharp pain, swelling, numbness, chest pain, dizziness, pain ≥ 7 or a fall → `SAFE-01`, area blocked until the user clears it | **None.** The model is never called |
| 3. Restrictions | Joint → blocked patterns (knee: loaded deep flexion, jumps, lunges; shoulder: overhead press, dips; lower back: loaded spinal flexion, floor deadlifts; wrist: floor push-ups, front rack) | — |
| 4. Substitutions | Same primary muscle, allowed pattern, available equipment, lowest joint-stress score | `P-08` names the swaps the app chose |
| 5. Duration | Mild 7–14 days, moderate 14–28; pain check after each related session | — |
| 6. Return | Pain ≤ 2 for 3 sessions → movement back at 50% load, +10–20% per session | Encouraging wording |
| 7. Escalate | Pain ≥ 4 twice or getting worse → stop that area, recommend a professional | Fixed text, no model |

The protocol is an `injury_protocol` proposal the user applies. "ASCEND is not a medical
device" appears in every protocol.

---

## 7. Readiness check-in

A 20-second check-in when the app opens (planned, Phase 4): sleep 1–5, energy 1–5, soreness
(none / some / a lot, tap the muscle), mood 1–5.

```text
readiness = 100 × (0.35·sleep + 0.30·energy + 0.20·(1 − soreness) + 0.15·mood)
            each input scaled 0–1; weights are estimates
green ≥ 70 · amber 50–69 · red < 50
```

| Band | Effect (rules) |
|---|---|
| Green | Today's plan unchanged |
| Amber | Workout quest cut by one set per exercise |
| Red | Swapped for mobility; the session moves to the next free day |
| Skipped check-in | Nothing changes |

"Still sore" on a muscle overrides its computed readiness for 24 h. The model's only job here
is `P-09`, one sentence describing the effect the rules chose. Readiness also feeds the
reactive deload signals (§2).

---

## 8. Tests that keep the AI out of the numbers

- Golden-file tests for each engine version (planner, progression, deload, weekly review,
  readiness).
- Property tests: a proposal never exceeds 1.5 × planned volume, never adds a blocked
  pattern, never sets kcal below the floor.
- Tool tests: every `propose_plan_change` call from recorded model outputs either maps to a
  rule or returns `accepted: false`.
- Number fidelity on 100 generated weekly reviews (metric M10, must be 100%).
