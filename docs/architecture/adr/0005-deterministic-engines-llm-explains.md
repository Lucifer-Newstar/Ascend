# ADR-0005: Deterministic Engines Decide; the LLM Only Explains

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

A fitness app gives advice that can injure people. Small local models hallucinate
numbers and cannot be unit-tested. Users must be able to switch AI off. The team must be
able to explain every number in an interview or viva.

## Decision

Every number and every plan change comes from **pure, deterministic Python engines**
with a version constant (`ALGO_VERSION`). The language model:

- receives the engine's numbers and findings and **writes explanations, summaries and
  conversation** only;
- can call tools such as `propose_plan_change`, which create a **proposal** the user
  must Apply / Edit / Keep — never a direct edit;
- is bypassed entirely for red-flag symptoms;
- has its output checked: any number not present in its input → the reply is replaced
  by the template version.

With AI off, templates produce the same text slots. Derived rows store `algo_version`;
formula changes ship as migrations that replay history; golden-file tests pin versions.

## Consequences

### Positive

- Testable: unit + property tests on every rule; reproducible results.
- Safe: no model can silently change training load or calories.
- Works on any PC, including without a GPU.
- Explainable to users ('why?') and to interviewers.

### Negative / Trade-offs

- Rules are more work to design than prompting a model.
- Explanations are only as good as the findings the rules produce.
- Some 'smart' features (free-form plan generation) are deliberately limited.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| LLM generates plans directly | Unverifiable, unsafe, not reproducible. |
| LLM with JSON schema output for numbers | Still model-dependent numbers; fails the AI-off requirement. |
| No LLM at all | Loses the conversational coach and multilingual explanations the product needs. |
