# Academic demonstration checklist

Status: unexecuted checklist, 22 November 2026. Check a box only after collecting evidence. This is not a claim that the current installer has passed.

## Record the build

- [ ] Choose a tested commit and matching Windows installer; record SHA-256, version, build source and CI run. Do not mix an old release with features documented only on main.
- [ ] Record Windows version, architecture, CPU, RAM, GPU (if any), power mode and free disk space.
- [ ] Use a separate disposable Windows account or otherwise isolated test installation/profile. Back up existing data first. Do not demonstrate using anyone's real health records or photographs.
- [ ] Expect an unsigned-installer SmartScreen warning; explain it honestly. Do not disable machine-wide security settings for the demo.
- [ ] Prepare fictional workout/meal history and explicit labels that it is demo data.

The development seeder is `app.devtools.seed_demo`, documented in its module and in the [local setup guide](../development/local-setup.md). It writes to the configured database; `--wipe` deletes data. Use it only with an explicitly isolated disposable `ASCEND_DATA_DIR`. Do not point it at the installed app's live data or bypass its installed-data safeguard. Development screenshots and a seeded development DB do not prove installer behaviour.

## Offline core, Ollama stopped

Record each result, not just the final screen. Disable external networking for the test while leaving localhost available for the sidecar. Stop Ollama and record its state. Do not download models or use optional online exercise lookup during the journey.

| Task | Expected observation | Actual result / evidence |
|---|---|---|
| Create fictional profile | Profile saved; estimates labelled appropriately | Not run |
| Log prepared workout | History and derived values update | Not run |
| Log meal manually | Search/portion and totals work; values approximate | Not run |
| Inspect suggestion | Inputs, reason and rule/version can be traced | Not run |
| Cancel then confirm a trainer change | Cancel does not mutate; confirm applies once | Not run |
| Restart | Profile/logs persist and remain usable offline | Not run |

- [ ] Check a deliberately chosen low-readiness case activates the recovery hold. State that readiness is computed, not measured biological recovery.
- [ ] Check supported undo, duplicate confirmation and the documented boundary for non-undoable changes.
- [ ] Export and re-import in a disposable profile; compare relevant record counts/values. Never overwrite a user's database to demonstrate restore.
- [ ] Test backup/restore in isolation, including photos if present. Backups are unencrypted; keep them private.
- [ ] Record failure behaviour if the sidecar is interrupted, using a disposable database. Inspect integrity and report missing/duplicate records instead of assuming recovery succeeded.
- [ ] Record cold start and memory usage; use at least 50 samples for an empirical p95 interaction latency, with timing boundaries and warm-up documented. Do not present Linux build-machine timings as Windows measurements.

## Review sequence

1. State the [problem and limits](academic-scope.md), build and offline conditions.
2. Log a workout, open its suggestion and connect explanation inputs to stored records.
3. Show the hold-triggering case and why it is an estimate.
4. Cancel and confirm a trainer change; show persistence and one manual meal entry.
5. Show baseline results, failures and individual contribution evidence.

## Fallback and boundaries

- [ ] Keep a local backup recording of the same tested build and journey. Label a recording as a recording, not a live demo.
- [ ] Keep the installer, approved report/slides and non-personal evidence available without internet.
- [ ] Do not present hidden food-photo code as trained functionality. No trained food model exists.
- [ ] Do not claim a trained LLM, clinical accuracy, injury prevention, guaranteed security or superiority to commercial apps.
- [ ] Every member rehearses their own implementation/testing contribution and the overall architecture. Navin is the team lead, not the sole author.

Save results using the [evaluation report template](evaluation-plan.md#run-report-template). A clean CI run, checklist or polished screenshot is not a substitute for observed Windows results.
