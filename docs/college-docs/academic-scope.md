# Academic scope and problem statement

Status: proposed scope for the team's guide to review, 22 November 2026. This is not an approved title, university rubric or completed user study. Navin leads ASCEND as a team project; evidence of individual contributions must be recorded rather than inferred from planned roles.

## Suggested title

**ASCEND: An Offline, Explainable Fitness Planning and Progress-Tracking System**

Here, explainable means inspectable rules, inputs and reasons. It does not claim a new explainable-AI technique.

## Problem statement

For adult recreational exercisers who prefer to keep fitness records on a Windows PC, maintaining workout and meal logs does not by itself make the next training decision transparent. This project addresses a bounded software-design problem: how to combine local record keeping, inspectable progression and recovery estimates, and user-controlled planning changes in one application that remains usable without an internet connection or a generative model.

ASCEND integrates workout history, self-reported effort and optional daily check-ins into deterministic, versioned suggestion rules. It exposes the reasons and inputs behind suggestions and requires confirmation before trainer-proposed changes affect stored records. A manually searchable Indian-food log and lightweight gamification support the workflow. Evaluation should measure offline functionality, explanation consistency, action integrity, reproducibility and task usability. It must not claim to diagnose conditions, measure physiological recovery, prevent injury or prove improved fitness outcomes.

The preference for a Windows-only local workflow is a target-user hypothesis, not a demonstrated unmet market need. A PC is less convenient than a phone at the gym; ask intended users whether the workflow fits before claiming demand.

See the [auditable decision-loop proposal](proposal-auditable-decisions.md) for the literature-grounded design/evaluation angle: inspect inputs and reasons, choose whether to apply the change, then verify and undo where supported. It does not claim market exclusivity. Official [AU rules and review windows](anna-university-r2021.md) are recorded separately.

## Assessed core and boundaries

| Core | Supporting or optional | Outside the completed-work claim |
|---|---|---|
| Workout logging and history | Quests, XP, ranks and cosmetics | Trained food-photo recognition: no food model is trained |
| Versioned progression/recovery estimates and their explanations | Manual Indian-food logging with approximate portions | Clinical recovery accuracy or injury prevention |
| User-confirmed trainer changes and supported undo paths | Local intent router and cited retrieval | Guaranteed privacy/security from local storage alone |
| Local persistence and a tested Windows offline journey | Optional Ollama phrasing | A newly invented large language model |

Existing features are not deleted by this scope. It selects what the team can defend and demonstrate reliably. Pin one tested commit and installer; the README distinguishes released features from unreleased main-branch work.

## Existing-system comparison

Official descriptions checked on 22 November 2026, not a hands-on benchmark:

| System | Relevant documented capability | Consequence for ASCEND's claim |
|---|---|---|
| [Fitbod](https://help.fitbod.me/hc/en-us/articles/360004429814-How-Fitbod-Creates-Your-Workout) | Adaptive workouts based on goals, equipment, history and estimated recovery; [muscle recovery](https://help.fitbod.me/hc/en-us/articles/360006269014-Muscle-Recovery) is already an explicit feature | Recovery-aware planning is not new. No superiority in physiological accuracy is established. |
| [Hevy](https://help.hevyapp.com/hc/en-us/articles/33106320824727-Everything-You-Need-to-Know-About-the-Hevy-App-2026-Features-Guide) | Workout/routine/progress tracking; Pro includes personalized programs and progressive-overload suggestions | Do not describe it as only a basic logger. Logging and adaptive guidance are not unique. |
| ASCEND | Local Windows architecture; inspectable rule implementations; confirmed trainer changes; integrated logs and gamification | Evaluate the integration and engineering evidence, not a claim that competitors cannot operate offline. |

Vendor pages do not establish competitors' missing features, cloud dependence or inferior privacy. Do not infer those negatives from a short feature summary.

## Measurable objectives

These are proposed acceptance targets to agree with the guide **before** measurement, not results:

| ID | Objective | Proposed acceptance evidence |
|---|---|---|
| A1 | Offline core operation | On a named Windows 10/11 x64 laptop with networking disabled and Ollama stopped, complete 6/6 tasks: profile, workout log, meal log, inspect suggestion, confirm/cancel trainer change, restart with persistence. Record the exact installer/commit and results. |
| A2 | Explanation consistency | For 30 fixed recovery/progression cases, displayed inputs, rule/version and reason agree with engine output in 30/30. Include missing effort ratings, cold start and conflicting check-ins. |
| A3 | Action integrity | At least 20 confirmation/cancel/duplicate-confirmation/supported-undo cases: zero writes before confirmation and zero duplicate writes. Identify non-undoable operations explicitly. |
| A4 | Reproducible evaluation | Rerun existing synthetic baselines with saved seeds/configuration and add cases that activate the recovery hold. Report calibration, errors and tradeoffs. Do not call simulated readiness measured biological truth. |
| A5 | Task usability | If the guide approves, 5-8 consenting adult volunteers attempt the same six tasks. Proposed target: at least 80% unassisted completion across participant-task attempts. Report numerator/denominator, time, errors and explanation comprehension. This small convenience sample cannot establish population-level or health effects. |

See [evaluation plan](evaluation-plan.md), [demo checklist](academic-demo.md) and [contribution evidence](contribution-evidence.md).

## Priority order

1. **P0:** agree this scope/title and pin the demonstration version.
2. **P1:** verify the installed Windows offline journey, backup/restore and failure handling; keep a backup recording.
3. **P1:** verify explanation and action traces against reproducible cases.
4. **P2:** add stress scenarios and a guide-approved usability protocol before expanding features.
5. **P2:** if the optional language layer is assessed, freeze independent questions before tuning and report per-class errors, macro-F1, coverage and abstention.
6. **P3:** assemble truthful contribution, citation, dataset-licence and tool-use records for the report and individual viva.

Department confirmation is still needed for the topic, review rubric, report template, consent and AI-use requirements. Do not invent a similarity percentage, compulsory publication or clinical trial requirement.
