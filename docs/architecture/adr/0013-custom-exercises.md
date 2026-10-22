# ADR-0013: Custom Exercises: Rules First, Local Model Second, Online Only on Request

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Navin Jairam M (lead)

## Context

The bundled library (free-exercise-db plus ASCEND's own calisthenics progressions) will
never cover everything people train. Users need to add their own exercises, and those
exercises must work everywhere a library exercise works: muscle load, quests, stats,
history, import/export.

What a custom exercise needs is muscles mapped onto the 19 regions, a measure (reps, hold
or time), a section and a pattern. If those are wrong, readiness and quests go wrong too. At the same time:

- the app is offline-first (ADR-0009);
- AI is optional and only explains or suggests (ADR-0005, ADR-0011);
- users must be able to see where every value came from.

## Decision

1. **Analyse, review, then create.** `POST /exercises/analyze` proposes every field.
   Nothing is saved until the user confirms the form (`POST /exercises`).
2. **Four stages, each optional except rules.** Each field records the stage that set it in `field_sources`:
   1. `library`: fuzzy match against the library.
      - Close matches are offered as "did you mean".
      - A match scoring 0.85 or more seeds the proposal.
      - An exact or alias match blocks creation (409), which prevents duplicates.
   2. `rules`: keyword rules for equipment, section, measure, pattern, muscles, difficulty and rep range.
      The rules always produce a complete proposal.
   3. `local_ai`: qwen3:4b through Ollama on localhost, prompt `exercise_classify.v1`, with a JSON schema sent as `format`.
      - The reply is validated field by field: enum values, known muscle regions, at least one primary muscle, instruction length.
      - Invalid fields are dropped and the earlier value stays.
      - If AI is off, the model is not installed, or the reply is invalid or errors, the stage is skipped and its status is reported. The flow never blocks on the model.
   4. `wger` (online research): see decision 8. wger's licence, author and a link are stored as attribution.
3. **The user has the last word.** Any field the user edits in the review form is sent with source `user`.
   The detail page shows each field's source.
4. **Strict validation on create.**
   - Muscle regions must be known; weights must be between 0.25 and 1, with no duplicates.
   - At least one region is required, except for mobility and meditation.
   - `rep_low` must be ≤ `rep_high`.
   - MET is accepted only for time-based exercises.
   - Instruction and alias lengths are bounded.
   - A custom hold exercise follows the same rules as library holds (seconds are required).
5. **Event.** Creation publishes `ExerciseAdded` (with `field_sources`) through the outbox, so the future intelligence layer knows which fields were guessed.
6. **Removal archives.** Removing a custom exercise archives it: it is hidden from the library and pickers, but its sets, PRs and stats stay. Library exercises cannot be removed.
7. **Quests.** Quest suggestions draw from ASCEND's core list, the user's custom exercises and any library exercise they have logged. Quest progress counts sets by muscle, so custom exercises count automatically.
8. **Confidence and "not enough offline data"** (amended 2026-10-21, PR #48).
   - Every proposed field gets a confidence from the stage that set it:
     - **high**: the user, an exact-name wger match, or a library exercise scoring ≥ 0.95;
     - **medium**: a looser library match (0.85–0.95), a validated local-model answer, or a keyword rule that matched;
     - **low**: a rules fallback (no keyword matched: equipment "other", section "gym" with no equipment clue, pattern "other", difficulty "intermediate") or no value at all.
   - The core fields are section, equipment, measure, pattern and muscles. If any is low, `insufficient` lists it (muscles are not required for meditation and mobility).
   - The review then says so in plain words and asks "Look it up online?" with **Allow once**, **Always** (turns the setting on) and **No**.
   - These are rule-based levels, not calibrated probabilities. They say which stage a value rests on.
9. **Online research: consent, sources and the report** (amended 2026-10-21, PR #48).
   - **Consent.** `POST /exercises/analyze` sends requests only when it is **permitted** (Settings → "Online research" is on, or the request carries `allow_once`) **and wanted** (the user asked with `online`, or the setting is on and the offline proposal is insufficient).
     - Otherwise no HTTP client is created and no socket is opened. `test_zero_network_calls_when_research_is_off` asserts this by replacing the HTTP client, `socket.connect` and DNS resolution.
     - The setting is stored as `online_lookup` (the key name is unchanged for compatibility) and is off by default. Turning it on needs a consent step in Settings.
     - While it is on, the app header shows an "Online research on" indicator and the sidebar footer says that exercise names leave the PC.
   - **What is sent.** Only the exercise name, with an identifying User-Agent (`ASCEND-desktop/<version>`). Wikimedia's User-Agent policy asks for contact details; a packaged release should add a project URL or e-mail there.
   - **Sources checked:**

     | Source | Terms / licence | Used for |
     |---|---|---|
     | wger.de REST API (`/api/v2`) | Public read API, no key needed for reads. Exercise content is CC-BY-SA 4.0; each exercise reports its licence and author, both stored in the attribution | Fields: muscles (English names, plus Latin names when `name_en` is empty), equipment, cardio category, instructions |
     | Wikipedia REST `page/summary` | Text CC BY-SA 4.0 (attribution and share-alike); Wikimedia API etiquette: identify the client, keep request rates low | A two-sentence summary in the report, with link and licence. Never used for structured fields. Only accepted when the article title matches the name, because a redirect to a broad article such as "Exercise" is not evidence |
     | Wikidata | CC0 | Checked but **not queried**: exercise items carry no muscle or equipment statements (a search for "pallof press" returned nothing), so a request would add nothing |

   - **wger has no working search.** Its search endpoint answers 404, the `exercise-translation?name=` filter is exact and case-sensitive, and unknown filters are silently ignored (the API then returns every exercise).
     - So the lookup tries at most 6 spellings: as typed, Title Case, Sentence case and lower case, each also with "push-up"-style hyphens.
     - A result is accepted only when its normalised name equals the normalised query.
     - Names that wger spells differently (plurals, other word order) are not found. This is reported honestly as "nothing found" and the offline proposal stands.
   - **Failures never block.** Timeouts (6 s read, 4 s connect), no connection, HTTP 429 and other errors are caught per source and reported as `offline`, `timeout`, `rate_limited` or `error`; Wikipedia is skipped when wger already showed the network is down. The analysis still returns the offline proposal.
   - **Research report.** The response carries:
     - `research`: the query, consent (`setting` | `once`), outcome, every request with its status, the Wikipedia summary, and one row per field online research filled (value, source link, the offline value it replaces, and whether they conflict);
     - `offline` and `offline_sources`: the proposal before research.
     - The UI shows this as a report above the review form. The user can keep the offline guess per field, edit anything, and must press "Add to my library". Nothing is saved by the analysis.
   - **Local lookup log.** Each research request writes one `online_lookup_log` row (migration 0012): time, query, the sources asked with each request's URL and status, the outcome and the consent.
     - `GET /exercises/online-log` lists it, newest first; `DELETE` clears it. Settings shows it with a Clear button.
     - Blocked attempts are not logged, because nothing was sent.
   - Researched values reach the intelligence layer through the same `ExerciseAdded` event, whose `field_sources` tag them `wger`.

## Consequences

### Positive

- Works fully offline. With no model installed, the rules proposal is complete and still reviewable.
- Every value is traceable to its source, which matters for a 4B model's guesses.
- Duplicates of library exercises are caught before they split a user's history.

### Negative / Trade-offs

- Keyword rules are crude for unusual names. The review step exists for exactly this, and the model or wger can improve the proposal.
- wger's public API only filters by exact name (its search endpoint is not available). Online research tries a few casings, but finds an exercise only when the name matches wger's spelling.
- Confidence levels are rule-based (which stage set a value), not calibrated probabilities.
- Muscle weights from wger and from the model are coarse (primary 1.0, secondary 0.5).

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Model-first, rules as fallback | The model is optional and may be absent. Rules-first gives the same baseline on every machine, and the model's output can only refine it |
| Free-text muscles | They would break muscle load and quests, which key on the 19 regions |
| wger on by default | Contradicts offline-first and the privacy promise. The user must opt in (the setting) or allow a single lookup |
| Download all of wger's exercises once and search locally | It would sidestep the exact-name limit, but means a large CC-BY-SA dataset to bundle and attribute per exercise, and a sync to keep fresh. Deferred |
| Wikipedia text as instructions | An encyclopaedia summary is not coaching instructions, and share-alike text mixed into fields muddles attribution. It is used as a cited summary only |
| Hard delete | Would orphan logged sets and PRs |

## Validation

- `tests/api/test_custom_exercises.py` covers: the rules-only path, library matches and duplicates, the model mocked (valid, invalid and error replies), no model installed, online lookup gated by the setting and the per-request ask (wger mocked), creation, then logging, muscle load, the outbox event and quest refs, validation errors and archiving.
- `tests/unit/test_custom_rules.py` covers the keyword rules.
- `tests/api/test_online_research.py` (wger and Wikipedia mocked) covers:
  - zero network requests when research is off;
  - per-field confidence and `insufficient`;
  - allow once leaving the setting off;
  - the setting researching only insufficient proposals unless asked;
  - nothing saved by analysis;
  - a wrong-name wger result being rejected;
  - the Wikipedia title check;
  - offline, timeout and 429 handling;
  - the log listing newest first and clearing;
  - researched sources surviving creation.
- `AddExercise.test.tsx`, `Settings.test.tsx` and `Layout.test.tsx` cover the prompt and its three answers, the report and "keep offline", the log and Clear, and the header indicator, each with an axe check.
