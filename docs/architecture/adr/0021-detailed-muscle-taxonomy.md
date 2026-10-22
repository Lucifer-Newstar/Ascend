# ADR-0021: Detailed Muscle Taxonomy (muscles-v2) and Rule-Based Mapping (muscle-map-v1)

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Navin Jairam M (lead)

## Context

Up to v7, ASCEND tracked 19 coarse regions (taxonomy v1). The owner asked for a map at the
level strength-training resources use: the pectoralis major heads, the three deltoids, the
biceps and triceps heads, the four quadriceps, the three hamstrings, the glutes, the core
layers, and any other muscle that can be meaningfully targeted in a gym. Every exercise
(about 940) has to be re-mapped, every engine (recovery, quests, deload, coach, skill links,
custom exercises) has to read the new keys, and existing users must keep their history.

Research (all in `docs/research/`):
- `v8-anatomy.md`: location, actions and superficial/deep layer of each muscle; what was
  added, rolled up or left out, with sources.
- `v8-exercise-muscle-mapping.md`: EMG/MRI/hypertrophy evidence for head- and
  muscle-specific emphasis and a deterministic rules table.

## Decision

1. **54 keys** (`progress/taxonomy.py`, `TAXONOMY_VERSION = "muscles-v2"`), grouped region →
   muscle → head: Chest 4, Back 12, Neck 2, Shoulders 3, Arms 9, Core 4, Hips 5, Thighs 11,
   Lower legs 4. The research pass left out coracobrachialis and folded levator scapulae into
   the upper trapezius (no exercise loads either on its own); adductor brevis and pectineus
   roll up into adductor longus, multifidus into the erectors and anconeus into the triceps
   medial head. The anatomy document gives the reason and source for each.
2. **Numbers are estimates.** Heads inherit their parent's half-life, weekly target and
   capacity. 17 small, deep or rarely loaded muscles (rotator cuff, pectoralis minor,
   serratus, neck, transversus, quadratus lumborum, hip flexors, TFL, sartorius, gracilis,
   glute minimus, tibialis anterior, fibularis) are `readiness_only`: the map shows their
   recovery, but they never raise an "under-trained" or volume warning, because no evidence
   supports weekly set targets for them.
3. **muscle-map-v1** (`progress/muscle_map.py`, rules in
   `workouts/library_data/muscle_rules.json`): for each free-exercise-db coarse muscle
   (primary x1.0, secondary x0.5) the first rule whose keyword pattern matches the name wins
   (incline, decline, fly, dip, overhead, pushdown, hammer, preacher, seated calf, leg
   extension, abduction, shrug, row...); add-ons give muscles the source never names
   (serratus on push-ups, grip on hangs, erectors on barbell squats); weights combine with
   max; under 0.2 is dropped. Deterministic, about 30 lines, unit-tested on a golden table.
4. **Migration 0018** keeps a copy of the v7 rows, re-maps free-exercise-db exercises from
   their source lists, and translates hand-made weights (ASCEND's own, calisthenics,
   activities, custom) through the research table: *copy, not split*, so a muscle's
   readiness does not jump on migration day. Quest metrics are renamed and every stored
   dose is recomputed from the logged sets. No set, meal, XP or quest is deleted. The
   sidecar writes a pre-migration backup first; the downgrade restores the saved rows.
5. **Custom exercises** still get a first guess per coarse region (rules, local AI or
   wger), then `refine_legacy` splits it into heads using the name's keywords. The local AI
   picks among the 19 coarse regions only, which a 4B model does reliably.
6. **API.** `MuscleState` gains `region`, `parent`, `deep` and `readiness_only`; `map_slug`
   is now the key itself. Contract `progress.yaml` updated.

## Consequences

- One set now counts on several keys, so weekly effective sets per region rise. Targets moved
  with them (heads inherit the parent's target, so each head reaches it at about the same set
  count as the old region did).
- The recovery evaluation was re-run on the new keys; old and new numbers are side by side in
  `docs/ai/evaluation.md`.
- The weights are a model, not a measurement. The detail view says so, and the user can edit
  any exercise's muscles.
