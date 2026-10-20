"""The intelligence layer: deterministic engines that decide numbers (ADR-0005).

recovery      E1 per-muscle fatigue and readiness, personalised decay (recovery-v2)
progression   E2 next-session targets with reason codes (prog-v1)

Engines are pure functions of their inputs (no database, no clock, no I/O), so they are
unit-tested on hand-computed fixtures, property-tested, and replayed by the evaluation
scripts in services/sidecar/eval/. The services next to them load data and store results.
"""
