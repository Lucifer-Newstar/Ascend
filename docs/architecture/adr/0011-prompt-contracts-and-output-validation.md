# ADR-0011: Prompt Contracts and Output Validation

- **Status:** Accepted (lead decision, 2026-10-20; revisit at the Phase 0 kickoff if the team objects)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); Jegatheesan K (coach owner); ratified by the team at kickoff

## Context

ADR-0005 says engines compute every number and the model only explains. The v0.1 skeleton
enforces that only by asking the model ("use ONLY the numbers in the provided facts") in a
free-text prompt; nothing checks the reply. A 4B local model will sometimes invent a number,
name a diagnosis or claim to have changed a plan, and a prompt change can silently make that
more frequent. We need a rule that makes "the model only explains" testable.

## Decision

1. **Prompts are versioned contracts.** Each prompt is a file
   `coach/prompts/<id>.v<N>.txt` with an entry in `registry.yaml` (id, version, model, input
   variables, output schema, owner). Rendering uses Jinja2 with `StrictUndefined`. Any change
   is a new version. All prompts are listed in [docs/ai/prompt-library.md](../../ai/prompt-library.md).
2. **Structured output where possible.** Every non-chat template declares a JSON Schema
   (2020-12, `additionalProperties: false`), sent as Ollama's `format` and validated again in
   the sidecar. Chat streams text; plan changes go only through the `propose_plan_change`
   tool, whose arguments carry no numbers.
3. **A fixed validator chain** runs on every model output: schema → fact ids → number
   fidelity → banned phrases → language → length
   ([coach-llm.md §5](../../ai/coach-llm.md#5-structured-output-and-validation)). Chat is
   checked sentence by sentence before the user sees it.
4. **Failure means the rules answer.** A reply that fails any blocking check is replaced by the
   rules/template text with `fallback_reason: check_failed`. No partial unchecked text is
   shown.
5. **Safety runs before the model.** Red flags, eating-disorder words, diagnosis and medicine
   questions get fixed replies without a model call.
6. **Every reply records** `prompt_id`, `prompt_version`, model digest and check results.
7. **CI gate:** a PR that changes a prompt, a model tier or the manifest must include an eval
   report from `make eval-coach` whose hashes match the PR and whose metrics meet the
   thresholds in [evaluation-ai.md §6](../../ai/evaluation-ai.md#6-regression-gates-in-ci).

## Consequences

### Positive

- "The model may not invent numbers" becomes a unit-tested property, not a hope.
- Prompt changes are reviewable diffs with evidence attached.
- The same validators check the AI-off templates, so template bugs are caught too.
- Interview-friendly: each guard is a small pure function.

### Negative / Trade-offs

- Some correct but creative answers are rejected (for example a rounded number outside the
  2% rule); measured as the `check_failed` rate, target ≤ 5%.
- Sentence gating adds about one sentence of latency (estimate).
- More code and fixtures to maintain than a single prompt string.
- Word lists for safety and Tamil are never complete; the prompt and post-checks remain as
  extra layers.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Trust the prompt (v0.1 status quo) | Untestable; a model or prompt change can regress silently |
| Constrained decoding only (`format`) | Guarantees shape, not truth: a valid JSON string can still contain an invented number |
| A second model as a judge | A 4B judge is unreliable and doubles latency; a cloud judge breaks ADR-0009 |
| No chat, templates only | Loses the conversational coach and Tamil explanations the product needs |

## Validation

Metrics M9 (fallback rate), M10 (number fidelity 100%) and M11 (red-flag routing 100%) in
[evaluation.md](../../operations/evaluation.md#ai-and-ml), plus the coach rubric in
[evaluation-ai.md §3](../../ai/evaluation-ai.md#3-coach-answer-quality).
