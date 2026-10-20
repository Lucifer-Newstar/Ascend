# ADR-0004: Ollama with qwen3:4b (Coach) and qwen3-vl:2b (Meal Items)

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead); ratified by the team at kickoff

## Context

The coach must run locally on the reference laptop (RTX 3050 Laptop, 4 GB VRAM, 12 GB
RAM) and chat in English, with Tamil as a goal. The v1 plan picked Llama 3.2 3B, but its
model card lists eight officially supported languages and Tamil is not one; it is also
text-only. Meal scans need a small vision-language model to list items on a plate.

## Decision

Use **Ollama** (installed by the user, `127.0.0.1:11434`) as the model runtime.

| Role | Model | Size (Ollama tag page) | Licence |
|---|---|---|---|
| Coach (ARC) | `qwen3:4b`, thinking off for speed | 2.5 GB | Apache-2.0 |
| Meal item finder (optional second opinion, [ADR-0012](0012-classifier-first-meal-scan.md)) | `qwen3-vl:2b` | 1.9 GB | per model card — check before release |
| Lite / OOM fallback | `qwen3:1.7b` | 1.4 GB | Apache-2.0 |

- **One GPU model at a time:** the job queue unloads the chat model (`keep_alive: 0`)
  before a VLM job and reloads it after ([docs/ai/model-manager.md](../../ai/model-manager.md)).
- Prompts and output validation: [ADR-0011](0011-prompt-contracts-and-output-validation.md);
  Tamil test plan and go/no-go: [docs/ai/multilingual-tamil.md](../../ai/multilingual-tamil.md).
- **Tamil is beta.** Qwen3's announcement lists Tamil among 119 languages, but quality
  from a 4B model is **unverified**. Test with 30 real questions before v1.0; if poor,
  answer in English and translate with IndicTrans2 (MIT; distilled ~200M, CPU — size
  and speed unverified).
- Models are listed in the app's model manifest with SHA-256 and minimum VRAM.

## Consequences

### Positive

- Runs fully offline on the reference laptop; Ollama handles GPU/CPU offload and quantisation.
- Simple HTTP API with streaming; easy to mock in tests.
- Swapping models is a manifest change, not a code change.

### Negative / Trade-offs

- Users must install Ollama separately (onboarding detects it and guides them).
- 4 GB VRAM forces model swapping; a scan adds a few seconds before the next chat reply (estimate).
- Small models can be wrong; mitigated by ADR-0005 (rules decide).

## Alternatives Considered

| Option | Why rejected |
|---|---|
| llama3.2:3b | No official Tamil support; text-only. Kept only as an English-only Lite option. |
| gemma3:4b | Multimodal and 140+ languages per its card, but 3.3 GB is tight on 4 GB; Gemma terms. Backup candidate. |
| qwen2.5:3b / qwen2.5-vl:3b | Research/non-commercial licence on the 3B models. |
| llama.cpp server bundled in the app | More control, but we would own GPU builds and model management; revisit if Ollama becomes a problem. |
| Hosted API (OpenAI, Gemini) | Violates offline-first (ADR-0009). |
