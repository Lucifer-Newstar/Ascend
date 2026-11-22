# v1.4.0-beta.1 published-payload verification

Checked 22 November 2026. This is a bounded functional check, not certification of every possible input, timing, OS integration or long-term outcome.

## Published release and gates

- [Release](https://github.com/Lucifer-Newstar/Ascend/releases/tag/v1.4.0-beta.1): published, not a draft, marked as a pre-release. The latest stable release remains [v1.3.0](https://github.com/Lucifer-Newstar/Ascend/releases/tag/v1.3.0).
- [Release-preparation PR #36](https://github.com/Lucifer-Newstar/Ascend/pull/36) was squash-merged through the ordinary merge path after all 16 current-head checks passed.
- Tag source: [`fdafe15bd2fafe9e976f28dae45463707e7a03ca`](https://github.com/Lucifer-Newstar/Ascend/commit/fdafe15bd2fafe9e976f28dae45463707e7a03ca). Exact-commit gates passed: [CI](https://github.com/Lucifer-Newstar/Ascend/actions/runs/44987122393), [Windows installer build](https://github.com/Lucifer-Newstar/Ascend/actions/runs/44987122432), and manually dispatched [ML](https://github.com/Lucifer-Newstar/Ascend/actions/runs/44987121994).
- [Tag publication workflow](https://github.com/Lucifer-Newstar/Ascend/actions/runs/44989399335) passed. No stable promotion or subsequent release was made.

## Downloaded artifact verification

Downloaded the actual public installer and checksum file from that release, rather than substituting the workflow's earlier build artifact.

| Item | Observed result |
|---|---|
| Installer | `ASCEND-Setup-1.4.0-beta.1.exe`, 179,504,263 bytes |
| SHA-256 | `46203fcd469b65563e676d2fec313206ecfc8f1a6ba48a3ab32e33d6c6f19672`, exactly matches published `SHA256SUMS.txt` |
| Archive | NSIS installer and embedded `app-64.7z` extracted successfully |
| App metadata | Extracted `resources/app.asar/package.json` reports `1.4.0-beta.1` |
| ASAR SHA-256 | `3d494e33c6bed9b9fdebc266858a4fe0311693e2945f42b30454473e45c46402` |
| App contents | The published ASAR is byte-for-byte identical to the exact-source Linux package's ASAR; all 1,932 compared `dist`/`dist-electron` files also match |
| Windows payload | `ASCEND.exe`, the frozen `ascend-sidecar.exe`, migration `0035_foods_v14.py`, intent model and knowledge assets are present |
| Pure-data comparison | All 39 compared migration and ML asset files match the exact-source Linux frozen-sidecar package |
| Electron hardening | All nine expected fuse settings pass `build/fuses.cjs --check` against the downloaded Windows `ASCEND.exe` |
| Photo policy | Published renderer CSP includes `blob:` only in `img-src`, as fixed by PR #35 |

Checksum agreement establishes download consistency, not publisher authenticity or Windows runtime correctness. The installer is unsigned; the release notes retain the SmartScreen warning.

## Execution environment and limits

The downloaded, unchanged `app.asar` was installed into the Linux Electron package for the post-publication runs below. It ran with Electron 45, the exact-tag Linux PyInstaller sidecar, an isolated fictional profile, production renderer CSP and real Electron IPC. No Vite dev server or mocked API was used. App info reported `1.4.0-beta.1`, the sidecar was ready with zero recorded restarts, and Node/require were absent from the renderer.

**This executes the published JavaScript/renderer payload, not the Windows executable or installer.** The Linux Electron executable and Linux sidecar are substitutions. Host restrictions required `--no-sandbox`; that does not validate the normal Windows sandbox. Real Windows install, launch, upgrade, uninstall and OS integrations remain **untested**.

## Post-publication functional matrix

The following passed on the published ASAR with the substitutions above. Writes used fictional local data only. Renderer exception listeners captured no JavaScript exceptions in the final runs.

| Feature | Exercise and result |
|---|---|
| First run | Name/body/goal/equipment onboarding, reveal and entry; profile persists on relaunch |
| Navigation | Main routes, unlock history and all six Settings sections render without page errors |
| Chat/action loop | Rule-based set proposal, explicit confirmation, remount with executed state, undo, and sidecar record checks |
| Strength | Select bench press; log, edit, delete and finish sets; completed workout appears in History |
| Calisthenics | Log a 30-second plank; start/stop a real stopwatch and persist elapsed seconds; finish session |
| Other activity sections | Log 75 seconds each for cardio (Brisk Walking), martial arts (Back Breakfall Practice), flexibility (90/90 Hamstring) and meditation (4-7-8 Breathing); verify persisted durations |
| Food | Search Idli, build and log the time-appropriate meal, then delete it and verify the record count |
| Body data | Log weight and a body measurement; inspect saved values |
| Morning readiness | Save a check-in, redo it, change energy and verify the saved change |
| Workout planner | Build a week, save and follow it; persisted following state is true |
| Built-in programs | Choose a program through Train and verify the current plan |
| Meal planner | Build vegetarian meals, save the plan, dismiss the save notification, delete the plan and verify removal |
| Goal checker | Enter current/goal weight and weeks; obtain the realistic-goal result |
| Custom exercise | Request local suggestions, add the required muscle, save to library, then remove |
| Custom skill | Choose a real library hold exercise, provide hold-mode criteria, save and delete the tree |
| Training schedule | Save Monday/Wednesday/Friday at 18:30; verify days/time after navigating away and back |
| Recovery evidence | Open a muscle's details and Why disclosure; formula inputs and personal/population comparison render |
| Photos | Upload a synthetic fixture, persist it, reveal it, then delete it. Earlier packaged verification also checked EXIF stripping |
| CSV import | Strong fixture preview, confirmation and duplicate prevention |
| Exports | JSON and both workout/meal CSV responses serialize current records; native file-save dialogs were not exercised |
| Backup/restore | Create manual backup, change units, restore backup and verify units roll back |
| Erase | Type the confirmation, return to onboarding, verify profile removal and a retained safety backup |
| Local shell helpers | Clipboard and keep-awake IPC return success; settings read/write persists |
| Game/coaching/progress | 46 successful feature-read calls cover game/boss/title/unlock state, coaching/team state, intent/knowledge status, diet/recovery/progression summaries and scheduling. Read success is not proof of every reward or calendar transition |
| Share privacy | Caption generation excludes the supplied fictional name and weight; nothing was posted externally |
| Optional models | AI-off status is correctly reported; intent and knowledge assets are available. Food-photo model is missing and remains unavailable, not a completed feature |

### Test-driver corrections, not app fixes

Initial driver attempts assumed breakfast after the app had switched its default to lunch, tried button selectors on radio/summary controls, omitted hold-mode criteria, and clicked a meal-plan Delete button behind a short-lived save notification. The final runs use the actual controls, dismiss the notification through its UI and check persisted records. The corrected paths pass. No app runtime patch was needed for those attempts.

### Automated checks and earlier fixes

- Release candidate: 614 frontend tests across 92 files pass; typecheck and production build pass; lint has zero errors and 22 existing warnings.
- The exact-commit CI above also passed Linux/Windows sidecar tests, Docker checks and the Linux frozen-sidecar smoke job. ML and Windows installer build/smoke checks passed separately.
- The release includes [PR #34](https://github.com/Lucifer-Newstar/Ascend/pull/34), including persisted action-card status after remount, and [PR #35](https://github.com/Lucifer-Newstar/Ascend/pull/35), the production photo-upload CSP fix. These are earlier fixes, not new post-release discoveries.
- The initial AI-off check found one copy error: the weekly-set list sent users to a muscle map on Today. The detailed map is now on Progress. The follow-up changes the hint to the correct panel and adds a regression test. It does not alter the beta assets or move the tag.

## Real local-model follow-up

After the initial AI-off matrix, installed a temporary Ollama 0.40.17 and pulled the actual `qwen3:0.6b` Q4_K_M model (522,653,767 bytes; digest `7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435`). No inference API, paid service or mocked model was used. The model ran locally on CPU with a 2,048-token context; this is not a performance claim for Windows or Qwen3:4b.

On the unchanged published payload and exact-tag sidecar, selecting that model made the AI self-test and coach tip return genuine model output. It also exposed a bug: the meal/workout planner, Why explanations and custom-exercise analysis read the configured default model instead of the user-selected model. Meal and explanation calls returned rules/templates while AI setup correctly reported the selected small model available.

This follow-up fixes selection in those callers and keys the explanation cache by selected model. Four routing/cache regression cases fail before the patch and pass after it. Related AI/planner/explanation tests, sidecar lint and types pass locally.

Retested with the published ASAR plus the patched Linux frozen sidecar: AI self-test, coach tip, an unknown trainer-chat question, meal-plan wording, workout-plan wording and TDEE explanation all return genuine Qwen3:0.6b output (roughly 1-4 seconds in this small test). Coach and explanation number/banned-phrase checks pass. The normal train-today question still takes its intended deterministic program-selection path. The custom-exercise selection fix has an automated routing test, not a successful end-to-end generative exercise-quality evaluation.

Plan quantities still come from deterministic engines; only their summaries are reworded. Not every chat answer uses an LLM: actions, FAQs, knowledge retrieval and routing remain rule/model-classifier paths. A generated chat sentence inferred recent logging activity despite an empty fictional log. Number checks are not a semantic truth guarantee; small-model factual reliability remains a limitation. No clinical accuracy or general response-quality certification is claimed.

These fixes are source changes awaiting green CI and normal merge. They are not in the already-published beta and no replacement release or tag rewrite was made.

## Still untested or intentionally excluded

- Real Windows installation, launch, migration of an existing Windows user's database, uninstall, auto-start, tray and notification behavior; Windows sandbox/security behavior.
- Native Save/Open dialogs and file-system destinations for exports/share images; real external posting/sharing; actual sound/hardware behavior.
- Default Qwen3:4b and larger models; broad prompt-quality/adversarial evaluation; live online research and permission/network-failure variants. No food-photo model exists to test end to end.
- Every exercise, trainer response, custom-tree criterion, equipment/program variant, timer boundary, reward/unlock scene, season/boss transition and multi-week streak/reminder scenario.
- Physiological accuracy, safety or real-user benefit. Synthetic engine metrics and passing functional tests do not establish these.

No new release was cut for the copy correction. The published beta remains the tagged payload described above.
