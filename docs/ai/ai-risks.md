# AI Risk Register

> Risks specific to ASCEND's AI features, with likelihood, impact, mitigation, owner and the
> signal that tells us a risk is happening. Reviewed at every phase gate by **Navin**; the
> project-wide register is [integration-edge-cases.md](../planning/integration-edge-cases.md).

Scales: likelihood and impact **L**ow / **M**edium / **H**igh, judged by the team (estimates,
not measurements).

---

## 1. Top five

1. **R2 Unsafe advice** — the cost of a wrong answer is an injury.
2. **R1 Hallucinated nutrition or numbers** — the most likely failure of a small model.
3. **R7 VRAM out of memory** — certain to happen on some PCs; must degrade gracefully.
4. **R4 Bias toward non-Indian food** — the core promise of the diet feature.
5. **R6 Licence problems** — can block a public release late.

---

## 2. Risk register

| Id | Risk | L | I | Mitigation | Owner | Signal / metric | Status |
|---|---|---|---|---|---|---|---|
| R1 | **Hallucinated nutrition or numbers**: the model states kcal, protein, loads or dates that no engine produced | H | H | Nutrients only from DB rows; numbers only from facts; number-fidelity validator V3 with sentence-gated streaming; rules text replaces a failing reply; VLM schema has no nutrient fields ([coach-llm.md §7](coach-llm.md#7-hallucination-guards), [food-recognition.md §6](food-recognition.md#6-nutrients-always-from-the-database)) | Jegatheesan | M10 = 100%; `check_failed` rate (M9) | Designed; validators planned Phase 2. **v0.1 replies are not yet number-checked** |
| R2 | **Unsafe advice**: training through a red-flag symptom, a diagnosis, medicine doses | M | H | Pre-filter before any model (EN, Tamil, Tanglish lists); fixed replies; injury protocol by rules; banned-phrase check V4; blocked patterns enforced in the planner; "not a medical device" in every protocol | Jegatheesan + Navin | M11 = 100% on `safety-40`; banned-phrase hits shown = 0 | Designed; Phase 2 |
| R3 | **Harm around eating**: advice that feeds restriction or guilt | M | H | Eating-disorder word list → `SAFE-02`; calorie floors in the engine; no guilt language (V4); calorie-deficit proposals paused 7 days after a match | Jegatheesan | Safety suite; rubric "Tone" | Designed; Phase 2 |
| R4 | **Bias toward non-Indian food**: the classifier, VLM or coach favour Western dishes and miss daily South Indian food | H | M | Class list from the team's own food diary; Indian datasets first, Food-101 only for transfer; per-cuisine-group metrics; INDB / IFCT as the nutrient source; coach prompt uses Indian food examples; personal swaps from corrections | Navin | Per-group top-3 on `test-own`; correction rate by group (M13) | Designed; Phase 1–2 |
| R5 | **Model too slow** on the reference laptop or weaker PCs, so users wait or give up | M | M | Tiers (Full / Lite / Off) from a speed test; `think: false`; 4,096-token context; first-token timeout 20 s → rules; streaming by sentence; classifier on CPU | Jegatheesan | M6, M7; fallback reason `slow` | Benchmark in Phase 2 |
| R6 | **Licence issues**: dataset terms forbid redistributing trained weights; model terms (Gemma, qwen3-vl) differ from Apache-2.0 | M | H | `ml/data/SOURCES.md` before first use; model card lists every source; train without any source that forbids redistribution; review model terms before offering a model; ADR-0006 notes | Navin | Licence column complete before v1.0 (release checklist) | **Unverified** for every dataset and for `qwen3-vl:2b` |
| R7 | **VRAM out of memory**: coach and VLM, or another GPU app, exceed 4 GB | H | M | One GPU model at a time (GPU lock, `keep_alive: 0` handover); classifier on CPU; `num_ctx` 4096; OOM → next tier, then rules; partial CPU offload shown, not hidden | Jegatheesan | `oom` fallback count; `ollama ps` split | Designed; Phase 2 |
| R8 | **Poor Tamil**: replies are wrong, stiff or misunderstood, and a safety message is missed | H | M | Beta label; "Show in English"; Tamil safety lists; human-translated fixed replies; go/no-go with a rubric; Path B (IndicTrans2) or Path C (English only) | Navin | M12 rubric mean; hard fails | **Unverified**; Phase 2 rating |
| R9 | **Prompt injection** from user text, food names or imported plan rows | M | M | Facts formatted and quoted by code; user message last and labelled; validators and filters do not rely on the model obeying; tool calls have no numbers and are checked by rules | Jegatheesan | Cassette tests with injection strings | Designed |
| R10 | **Over-trust**: users treat estimates (TDEE, kcal ranges, portions) as exact | H | M | Ranges instead of single values; "estimate" labels; sources shown per food; ETA as a range with confidence | Dhanush | Usability test notes | Partly implemented (TDEE marked estimate in v0.1 UI) |
| R11 | **Upstream model changes**: an Ollama tag is updated and behaviour shifts | M | M | Manifest pins the digest; a different digest is flagged `Unverified`; eval report bound to the digest in CI | Navin | `ai-eval-report` job | Designed |
| R12 | **Ollama missing or broken** (not installed, driver problems, port taken) | H | L | AI is optional; health checks; banner + rules mode; onboarding card explains | Jegatheesan + Dhanush | `ollama_unavailable` fallback count | v0.1 already falls back to rules |
| R13 | **Privacy leak** through a remote `OLLAMA_HOST` or an over-broad corrections export | L | H | Non-loopback host refused; crops-only export by default; consent per photo; egress test in CI | Navin | R7 egress test | Designed |
| R14 | **Miscalibrated classifier**: pre-selected chips are often wrong, so users stop checking | M | M | Temperature scaling; thresholds tuned for ≥ 90% pre-select precision; ECE gate | Navin | ECE, pre-select precision | Planned Phase 2 |
| R15 | **AI scope eats the schedule**: model work delays the core app | M | H | AI is optional by design; the cut order drops the VLM second opinion and Tamil beta before any core feature ([phases.md §6](../planning/phases.md#6-cut-order)); Tamil Path B and shadow mode are post-v1.0 by plan | Navin | Tracker burn-down | Active |
| R16 | **Formula bias**: Mifflin-St Jeor uses binary sex and population averages | M | L | Labelled as an estimate; adaptive TDEE from the user's own trend in Phase 4; user override of the target | Jegatheesan | — | v0.1 shows the estimate label |

---

## 3. How the register is used

- Each gate: update L / I and status; add any new risk found in testing.
- A risk whose signal crosses its threshold gets an issue with the owner and a date.
- A mitigation that changes architecture gets an ADR (as ADR-0011 and ADR-0012 did).
