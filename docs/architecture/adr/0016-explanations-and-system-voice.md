# ADR-0016: Explanations and the System's Voice

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Navin Jairam M (lead)

## Context

The engines (ADR-0014, ADR-0015) produce numbers with their inputs. Two needs follow.

- **Plain words.** People want a short reason in plain words. A local model (qwen3:4b via Ollama, ADR-0004) can phrase one, but it must never change or invent a number (ADR-0005, ADR-0011).
- **A voice for moments.** The app has a System window for game moments (level up, quest complete). Some engine moments deserve the same voice. Too many notices would make the System noise.

## Decision

1. **Templates first** (`intelligence/explain.py`, `explain-v1`).
   - Every target and every readiness has a deterministic one-line template built from the same facts the engine used.
   - That template is what users see by default.
2. **Optional phrasing.** When AI is on and the model answers, the model gets the facts block and the template and writes one sentence (at most 30 words, system prompt in `explain.py`).
3. **The coach guard decides.** The sentence goes through `coach/validate.py`:
   - V3: every number must appear in the facts, same unit;
   - V4: banned phrases (diagnosis, doses, "I changed your plan").
   - Any failure, timeout, missing model or AI off shows the template.
   - The response says which text was shown (`phrasing`), why the template was used (`fallback`) and the check results.
   - Passing sentences are cached per number (256 entries).
4. **Endpoints.** `GET /intelligence/progression/{id}/explanation` and `GET /intelligence/recovery/{muscle}/explanation`. The Why panels show the sentence with its source ("phrased by the local model, numbers checked" or "template").
5. **System notices** (`intelligence/notices.py`, `GET /intelligence/notices`). Only three kinds, at most one of each:
   - **deload:** the deload check recommends one this week;
   - **raised:** prog-v1 raised a target after the latest session (the biggest raise only, for 36 h);
   - **recovered:** a muscle trained in the last 4 days is at least 95 % recovered and today's quest trains it.
   - Ids are stable. The app shows an id once (remembered locally), at most one notice per refresh, in the existing SystemWindow.

## Consequences

### Positive

- No model output reaches the user unchecked, and every number on screen stays the engine's.
- The app is complete without the model: templates cover every case.
- The System speaks rarely, so its notices keep their weight.

### Negative / Trade-offs

- The guard accepts a sentence that uses only allowed numbers but frames them oddly. V3/V4 check numbers and phrases, not meaning.
- Phrasing quality with qwen3:4b is **unverified**: no Ollama was available on the build machine, so no real model sentence was ever produced or checked. The tests use a stub model. Measuring the guard pass rate on a real install is on the roadmap.
- Notice "seen" state is per device (localStorage), not in the database.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Let the model write the reason freely | Violates ADR-0005; numbers could drift. |
| No model at all | Templates are fine; phrasing is a small optional comfort with a strict guard. |
| Notices for every target change | Too chatty; the suggestion card already shows each change. |

## Validation

- `tests/api/test_intelligence_explain.py` covers: a passing sentence shown and cached; an invented number falls back; banned phrases fall back; model down, error or AI off falls back.
- `tests/api/test_intelligence_notices.py` and the desktop tests check each notice id is shown once.
