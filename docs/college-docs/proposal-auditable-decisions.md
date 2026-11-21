# Proposed contribution: an auditable fitness decision loop

Status: proposal for the guide and team, 22 November 2026. This is a defensible engineering/evaluation angle, **not a claim of invention, market exclusivity or clinical efficacy**.

## The angle to use

**Can a recreational exerciser inspect the evidence behind a suggested training change, understand its limits, choose whether to apply it, and verify or undo the resulting record change?**

Build the demonstration and evaluation around this loop:

1. **Evidence:** show the logged sets, effort and missing-data assumptions used.
2. **Reason:** show the deterministic rule/version, formula inputs and proposed target.
3. **Choice:** keep the existing plan, reject the proposal or explicitly confirm it.
4. **Verification:** show the resulting record/audit state, block duplicate confirmation, and offer undo where supported.

Local Windows operation is the delivery constraint. Indian-food logging and gamification support use, but are not the research contribution. This framing can be tested without pretending a readiness percentage is a measured physiological state or training a new large model.

## Why this is a real design question

[Su et al., 2021, *Analyzing Description, User Understanding and Expectations of AI in Mobile Health Applications*](https://pmc.ncbi.nlm.nih.gov/articles/PMC8075490/) analysed descriptions of 40 AI-labelled mobile health apps and related user reviews. Users wanted to understand recommendations and have their feedback incorporated; unclear explanations led users to construct their own accounts of system behaviour. This supports studying transparency and control as user needs. It does not establish that every current fitness app fails at them, or that a Windows tool will be adopted.

A [2025 systematic review of smartwatch-assisted ML exercise prescription](https://pmc.ncbi.nlm.nih.gov/articles/PMC12411723/) discusses limited interpretability in that research area. Its wearable scope is different from ASCEND's desktop prototype. Use it as adjacent literature, not proof of ASCEND's novelty or physiological validity.

Current commercial capability also matters: [Fitbod](https://help.fitbod.me/hc/en-us/articles/360004429814-How-Fitbod-Creates-Your-Workout) documents adaptive workouts and user adjustments; [Hevy's 2026 guide](https://help.hevyapp.com/hc/en-us/articles/33106320824727-Everything-You-Need-to-Know-About-the-Hevy-App-2026-Features-Guide) documents personalized programs and progressive-overload suggestions in Pro. Do not make them straw-man basic loggers or assert that they lack explanations, privacy or offline operation without a separate feature audit.

## What ASCEND can substantiate in code

- [Recovery engine](../../services/sidecar/app/modules/intelligence/recovery.py): deterministic calculation and exposed formula inputs.
- [Progression engine](../../services/sidecar/app/modules/intelligence/progression.py): reason codes and next-target explanations.
- [Action API tests](../../services/sidecar/tests/api/test_actions.py): a chat proposal does not log sets before confirmation; repeated confirmation is rejected; supported undo removes the logged sets; cancel and irreversible-operation rules are tested.

Those tests establish program behaviour for cases under test. They do not establish that every screen communicates it well, that the Windows installer works, or that suggestions are good for real people. Verify each layer separately.

## A bounded test that would strengthen it

Add to the [evaluation plan](evaluation-plan.md), with guide approval:

- Freeze 30 cases covering cold start, missing effort, a normal progression, low-readiness hold, cancel, duplicate confirmation and supported/non-supported undo.
- Check explanation values against engine output and audit/database state. Keep failures, not only successful screenshots.
- In the small consented task study, ask users to identify which logs changed the target, one missing-data assumption, whether anything was written before confirmation and how to reverse a supported change. Record correct answers and task completion with denominators.
- If comparing an explanation-visible view with a target-only view, label it exploratory, randomize/counterbalance order, and do not claim causal or population-level effects from 5-8 convenience volunteers. The comparison is optional, not a promised result.

The academic contribution is the designed, implemented and evaluated decision loop and its failure boundaries. A practical title can remain **ASCEND: An Offline, Explainable Fitness Planning and Progress-Tracking System**. Explainable refers to inspectable rules, not a novel XAI algorithm.
