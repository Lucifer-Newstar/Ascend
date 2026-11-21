# Packaged application verification, 22 November 2026

## Result

A locally built, unpacked Linux Electron app was launched with the real preload/IPC bridge and a frozen PyInstaller sidecar. This is stronger than a web-preview test, but it is **not a Windows installer certification**. Fictional local data only was used. No release was tagged or published.

The starting source was PR #34's merged commit `389c0d81a3b19830d9ce838dc7d65812e9641c62`. The version still reports 1.3.0 because unreleased work has not yet been versioned. Photo checks below include the narrow fix accompanying this report.

## Reproduced defect and fix

Progress-photo upload failed with a valid PNG in the packaged app. `reencodePhoto` decodes a local `blob:` object URL before drawing to a canvas, but the production image policy permitted only self and data URLs. The image decode failed before the API was called.

The fix permits `blob:` for images only. Script sources and `connect-src 'self'` remain unchanged; remote image origins are not enabled. A new policy regression test failed on the old policy, then passed. The rebuilt packaged app uploaded and displayed a synthetic 400 by 500 pattern, stored a JPEG with zero EXIF fields, and deleted it after confirmation.

## Passed in the packaged app

- First launch: fresh migrations through `0035`, authenticated sidecar ready, no Node `process` or `require` exposed in the renderer.
- UI onboarding: name/body fields, goal, equipment, reveal and entry. Profile persisted after relaunch.
- All 12 main routes and all six Settings sections opened with no non-empty error alert. Screens were captured and inspected. This checks rendering, not every control on each page.
- Trainer chat: a workout proposal did not log sets until Confirm; Confirm logged three sets; navigating away and back retained executed status; Undo removed them.
- Manual strength workout: log set, edit reps, add another set, delete that set, finish workout and see it in History. A one-set session correctly showed the insufficient-session-XP explanation.
- Fuel: search idli, build/log breakfast, verify persisted meal, delete it.
- Progress: log weigh-in and a body measurement, verify saved records.
- Planner: build a week, save and follow it, verify following state.
- Custom exercise: suggest offline details, explicitly add the required muscle, save and remove it. Missing muscle was rejected, not guessed.
- Progress photo: upload valid synthetic PNG, display, JPEG re-encoding, delete. See defect above.
- Strong import: choose fixture CSV, preview, confirm, then verify a second preview reports duplicates and zero new workouts.
- JSON and workout/meal CSV exports returned serialized records through real IPC. Native save-dialog completion was not tested.
- Back up now, change units, restore the manual backup via the UI, and verify units rolled back.
- Erase fictional data with typed confirmation: returned to onboarding, profile absent, safety backups retained.
- Settings write/read, clipboard write and keep-awake start/stop returned success. Real display-sleep prevention was not physically observed.
- No captured renderer JavaScript exceptions in either packaged run.

## Automated/build checks

- 614 frontend tests across 92 files passed after the fix (613 before it).
- Production renderer and Electron TypeScript build passed.
- Linux frozen sidecar and unpacked Electron packaging completed.
- The earlier merged PR had 16 successful GitHub checks across its current-head runs before merge, including Linux/Windows sidecar and desktop checks, Linux frozen-sidecar, Docker, docs and commit checks.
- Earlier bounded local backend results remain in [the prior report](../../college-docs/verification-2026-11-22.md). They are not relabelled as a full local backend run.

## Untested or limited

- Actual Windows NSIS install/uninstall, SmartScreen, Windows startup/login item, tray behavior, notifications, real sleep/wake and OS restart.
- Every exercise type: the UI strength loop was tested, not all timed/hold/cardio/martial-arts variants. Automated tests do not replace that manual matrix.
- Real Ollama model download/inference, generated phrasing, network research, microphone, recording, share-site side effects, native export/save dialogs, all image/video exports.
- All training schedules over real weeks, earned skills, seasonal bosses, every cosmetic/replay and every settings permutation.
- Hevy UI import and every malformed CSV or migration/restore combination. A synthetic fresh DB and manual backup restore are not a real team-DB upgrade rehearsal.
- Food-photo recognition: hidden without a trained approved model, not claimed complete.
- Clinical accuracy, injury safety, physiological outcomes and a real user study.
- Electron was launched with `--no-sandbox` in an isolated Linux test session because of the host's process restrictions. Application context isolation and Node-disabled renderer were observed, but this does not certify the installed Windows sandbox.
- Existing 22 frontend lint warnings and 14 moderate development-tool dependency advisories remain documented technical debt.

## Release state

No release tag or publication is authorized yet for the proposed `v1.4.0-beta.1` target. The repo assigns version/go-no-go to the lead; the beta workflow and notes are being prepared separately for review. A stable promotion must not be described as having passed three days of beta testing when it has not.
